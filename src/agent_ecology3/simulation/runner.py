"""Simulation orchestration for AE3 autonomous loop runtime."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from ..world.world import World


@dataclass
class LoopRuntimeState:
    artifact_id: str
    principal_id: str
    iterations: int = 0
    consecutive_errors: int = 0
    last_error: str | None = None
    running: bool = False


@dataclass
class RunnerStatus:
    running: bool
    paused: bool
    elapsed_seconds: float
    loop_count: int
    event_number: int
    summary: dict[str, Any] = field(default_factory=dict)


class SimulationRunner:
    """Run autonomous `has_loop` artifacts with resource-gated pacing."""

    def __init__(self, world: World) -> None:
        self.world = world
        self._running = False
        self._paused = False
        self._stop_requested = False
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._active_started_monotonic: float | None = None
        self._active_elapsed_seconds = 0.0

        self._loop_states: dict[str, LoopRuntimeState] = {}
        self._loop_tasks: dict[str, asyncio.Task[None]] = {}
        self._world_execution_lock = asyncio.Lock()
        self._target_llm_attempts: int | None = None

    def _settled_llm_attempt_count(self) -> int:
        # The stop boundary must not depend on the dashboard retention window.
        # Read the complete bounded run log and count unique trace custody so a
        # replayed settlement cannot consume another attempt slot.
        limit = max(1, int(self.world.logger.sequence))
        attempts: set[str] = set()
        for event in self.world.logger.read_recent(limit):
            if event.get("event_type") not in {"llm_syscall", "llm_syscall_error"}:
                continue
            trace_id = event.get("trace_id")
            attempts.add(
                str(trace_id)
                if isinstance(trace_id, str) and trace_id
                else f"event-sequence:{event.get('sequence')}"
            )
        return len(attempts)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def elapsed_seconds(self) -> float:
        elapsed = self._active_elapsed_seconds
        if self._active_started_monotonic is not None:
            elapsed += time.monotonic() - self._active_started_monotonic
        return max(0.0, elapsed)

    def _settle_active_time(self) -> None:
        if self._active_started_monotonic is None:
            return
        self._active_elapsed_seconds += (
            time.monotonic() - self._active_started_monotonic
        )
        self._active_started_monotonic = None

    def pause(self) -> None:
        if not self._paused:
            self._settle_active_time()
        self._paused = True
        self._pause_event.clear()

    def resume(self) -> None:
        if self._paused and self._running:
            self._active_started_monotonic = time.monotonic()
        self._paused = False
        self._pause_event.set()

    def stop(self) -> None:
        self._stop_requested = True
        self._stop_event.set()
        self._pause_event.set()

    async def _sleep_until_stop(self, delay: float) -> None:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=max(0.0, delay))
        except TimeoutError:
            return

    def get_status(self) -> RunnerStatus:
        return RunnerStatus(
            running=self._running,
            paused=self._paused,
            elapsed_seconds=self.elapsed_seconds,
            loop_count=len(self._loop_tasks),
            event_number=self.world.event_number,
            summary={
                "mint_enabled": self.world.mint_auction is not None,
                "frozen_agents": sorted(self.world.frozen_agents),
            },
        )

    def _discover_loops(self) -> list[tuple[str, str]]:
        discovered: list[tuple[str, str]] = []
        for artifact_id in self.world.artifacts.discover_loops():
            artifact = self.world.artifacts.get(artifact_id)
            if artifact is None or artifact.deleted:
                continue
            principal_id = artifact.owner
            if not principal_id:
                continue
            discovered.append((artifact_id, principal_id))
        return discovered

    async def _run_artifact_loop(self, state: LoopRuntimeState) -> None:
        cfg = self.world.config.simulation.loop
        delay = max(0.01, cfg.min_delay_seconds)
        state.running = True

        while not self._stop_requested:
            await self._pause_event.wait()
            if self._stop_requested:
                break

            artifact = self.world.artifacts.get(state.artifact_id)
            if artifact is None or artifact.deleted:
                state.running = False
                return

            # Hard resource gate on budget; freeze until budget returns.
            if self.world.ledger.get_llm_budget(state.principal_id) <= 0:
                self.world.freeze_agent(state.principal_id)
                await self._sleep_until_stop(max(0.05, cfg.resource_check_interval_seconds))
                continue
            self.world.unfreeze_agent(state.principal_id)

            async with self._world_execution_lock:
                # A sibling loop may have been waiting on the serial lane when
                # another loop reached an evaluation stop boundary.
                if self._target_llm_attempts is not None and self._stop_requested:
                    break
                result = await self.world.execute_action_data_async(
                    state.principal_id,
                    {
                        "action_type": "invoke_artifact",
                        "artifact_id": state.artifact_id,
                        "method": "run",
                        "args": [],
                    },
                    increment_event=True,
                )
                if (
                    self._target_llm_attempts is not None
                    and self._settled_llm_attempt_count() >= self._target_llm_attempts
                ):
                    self.stop()
            state.iterations += 1

            if result.success:
                state.consecutive_errors = 0
                state.last_error = None
                delay = max(0.01, cfg.min_delay_seconds)
            else:
                state.consecutive_errors += 1
                state.last_error = result.message
                delay = min(max(cfg.min_delay_seconds, delay * 2), cfg.max_delay_seconds)
                if state.consecutive_errors >= cfg.max_consecutive_errors:
                    self.world.logger.log(
                        "loop_paused_error_backoff",
                        {
                            "event_number": self.world.event_number,
                            "artifact_id": state.artifact_id,
                            "principal_id": state.principal_id,
                            "consecutive_errors": state.consecutive_errors,
                            "last_error": state.last_error,
                        },
                    )

            if self._stop_requested:
                break
            await self._sleep_until_stop(delay)

        state.running = False

    async def run(
        self,
        duration: float | None = None,
        *,
        target_llm_attempts: int | None = None,
        start_paused: bool = False,
    ) -> World:
        if self._running:
            return self.world
        if target_llm_attempts is not None and int(target_llm_attempts) <= 0:
            raise ValueError("target_llm_attempts must be > 0 when provided")

        max_runtime = self.world.config.simulation.max_runtime_seconds
        target_duration = duration if duration is not None else self.world.config.simulation.default_duration_seconds
        summary_interval = max(1.0, self.world.config.simulation.summary_interval_seconds)

        self._running = True
        self._paused = bool(start_paused)
        self._stop_requested = False
        self._stop_event.clear()
        if start_paused:
            self._pause_event.clear()
        else:
            self._pause_event.set()
        self._active_elapsed_seconds = 0.0
        self._active_started_monotonic = (
            None if start_paused else time.monotonic()
        )
        self._target_llm_attempts = (
            int(target_llm_attempts) if target_llm_attempts is not None else None
        )

        loop_pairs = self._discover_loops()
        self._loop_states = {
            artifact_id: LoopRuntimeState(artifact_id=artifact_id, principal_id=principal_id)
            for artifact_id, principal_id in loop_pairs
        }
        self._loop_tasks = {
            artifact_id: asyncio.create_task(self._run_artifact_loop(state))
            for artifact_id, state in self._loop_states.items()
        }

        self.world.logger.log(
            "simulation_started",
            {
                "event_number": self.world.event_number,
                "duration_seconds": target_duration,
                "max_runtime_seconds": max_runtime,
                "loop_count": len(self._loop_tasks),
            },
        )

        next_summary_at = self.elapsed_seconds + summary_interval
        loop_failures: list[BaseException] = []
        try:
            while not self._stop_requested:
                for task in self._loop_tasks.values():
                    if task.done() and not task.cancelled():
                        failure = task.exception()
                        if failure is not None:
                            raise failure
                await self._pause_event.wait()

                elapsed = self.elapsed_seconds
                if max_runtime > 0 and elapsed >= max_runtime:
                    self.world.logger.log(
                        "simulation_runtime_limit_reached",
                        {
                            "event_number": self.world.event_number,
                            "elapsed_seconds": elapsed,
                            "max_runtime_seconds": max_runtime,
                        },
                    )
                    break
                if (
                    self._target_llm_attempts is None
                    and target_duration > 0
                    and elapsed >= target_duration
                ):
                    break

                # A provider await may hold the serial world-execution lane.
                # Skipping mutable maintenance keeps duration monitoring independent.
                if not self._world_execution_lock.locked():
                    async with self._world_execution_lock:
                        self.world.tick()
                        if elapsed >= next_summary_at:
                            self.world.log_summary_snapshot()
                            next_summary_at = elapsed + summary_interval

                remaining = 1.0
                if self._target_llm_attempts is None and target_duration > 0:
                    remaining = min(remaining, max(0.01, target_duration - elapsed))
                if max_runtime > 0:
                    remaining = min(remaining, max(0.01, max_runtime - elapsed))
                await self._sleep_until_stop(remaining)
        finally:
            self._settle_active_time()
            self._stop_requested = True
            self._stop_event.set()
            self._pause_event.set()
            if self._loop_tasks:
                outcomes = await asyncio.gather(
                    *self._loop_tasks.values(), return_exceptions=True
                )
                loop_failures = [
                    outcome
                    for outcome in outcomes
                    if isinstance(outcome, BaseException)
                    and not isinstance(outcome, asyncio.CancelledError)
                ]

            self._running = False
            self._target_llm_attempts = None
            self.world.log_summary_snapshot()
            self.world.logger.log(
                "simulation_stopped",
                {
                    "event_number": self.world.event_number,
                    "elapsed_seconds": self.elapsed_seconds,
                    "loop_count": len(self._loop_tasks),
                    "loops": {
                        loop_id: {
                            "principal_id": state.principal_id,
                            "iterations": state.iterations,
                            "consecutive_errors": state.consecutive_errors,
                            "last_error": state.last_error,
                        }
                        for loop_id, state in self._loop_states.items()
                    },
                },
            )

        if loop_failures:
            raise loop_failures[0]

        return self.world
