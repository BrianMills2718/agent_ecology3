"""Fail-closed attempt custody for the bounded Plan 10 Luna PoC.

The journal stores provider-settled syscall results before the autonomous loop
can classify or apply them.  A restarted deterministic world replays those
results through the normal loop, so it can reconstruct local state without a
replacement provider dispatch.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal, NoReturn, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..config import AppConfig
from ..world.world import World

AttemptPhase = Literal[
    "dispatching",
    "provider_settled",
    "applying",
    "committed",
    "dispatch_ambiguous",
    "invalid",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RecoverableAttemptV1(_StrictModel):
    ordinal: int = Field(ge=1)
    attempt_id: str
    request_sha256: str
    payer_id: str
    model: str
    request: dict[str, Any]
    replay_observed_request: dict[str, Any] | None = None
    trace_id: str | None = None
    phase: AttemptPhase
    syscall_result: dict[str, Any] | None = None
    error: str | None = None


class RecoveryCheckpointV1(_StrictModel):
    schema_version: Literal["ae3_recovery_checkpoint.v1"] = "ae3_recovery_checkpoint.v1"
    run_id: str
    target_attempts: int = Field(ge=1)
    provider_dispatch_count: int = Field(default=0, ge=0)
    terminal_state: Literal["invalid", "stopped"] | None = None
    terminal_reason: str | None = None
    attempts: list[RecoverableAttemptV1] = Field(default_factory=list)
    updated_at: str


class RecoveryStatusV1(_StrictModel):
    schema_version: Literal["ae3_recovery_status.v1"] = "ae3_recovery_status.v1"
    run_id: str
    lifecycle_state: Literal["ready", "running", "paused", "completed", "stopped", "invalid"]
    target_attempts: int
    committed_attempts: int
    provider_dispatch_count: int
    last_attempt_id: str | None
    last_attempt_phase: AttemptPhase | None
    terminal_reason: str | None
    pid: int | None = None
    heartbeat_at: str


class RecoveryTerminalError(BaseException):
    """Stop the cell without allowing the loop to convert failure to fallback."""


class SimulatedRecoveryInterruption(RecoveryTerminalError):
    """Provider-free fault used to prove the two recovery boundaries."""


Syscall = Callable[..., Awaitable[dict[str, Any]]]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


_VOLATILE_CPU_RE = re.compile(r'("cpu_seconds_remaining"\s*:\s*)-?\d+(?:\.\d+)?')


def _request_sha256(request: dict[str, Any]) -> str:
    """Hash the semantic request while excluding measured local CPU jitter."""

    normalized = cast(dict[str, Any], json.loads(json.dumps(request, ensure_ascii=True)))
    messages = normalized.get("messages")
    if isinstance(messages, list):
        for message in messages:
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if isinstance(content, str):
                message["content"] = _VOLATILE_CPU_RE.sub(r'\g<1>"<runtime-local>"', content)
    return _sha256_json(normalized)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=True, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class RecoverableLoopWorld(World):
    """World whose existing loop publishes the local action commit boundary."""

    def build_loop_messages(
        self,
        *,
        principal_id: str,
        state_snapshot: dict[str, Any],
        strategy_text: str,
    ) -> list[dict[str, str]]:
        """Remove measured local CPU jitter from the recoverable decision contract."""

        stable_snapshot = cast(
            dict[str, Any], json.loads(json.dumps(state_snapshot, ensure_ascii=True))
        )
        resources = stable_snapshot.get("resources")
        if isinstance(resources, dict) and "cpu_seconds_remaining" in resources:
            resources["cpu_seconds_remaining"] = 0.0
        return cast(
            list[dict[str, str]],
            super().build_loop_messages(
                principal_id=principal_id,
                state_snapshot=stable_snapshot,
                strategy_text=strategy_text,
            ),
        )

    def _default_loop_code(self, principal_id: str, slot: int) -> str:
        code = super()._default_loop_code(principal_id, slot)
        needle = '    result = invoke("kernel_act", decision)\n'
        replacement = (
            '    if "kernel_actions" in globals() and hasattr(kernel_actions._world, "_recovery_mark_applying"):\n'
            '        kernel_actions._world._recovery_mark_applying(decision_meta.get("llm_trace_id"))\n'
            '    result = invoke("kernel_act", decision)\n'
            '    if "kernel_actions" in globals() and hasattr(kernel_actions._world, "_recovery_mark_committed"):\n'
            '        kernel_actions._world._recovery_mark_committed(decision_meta.get("llm_trace_id"))\n'
        )
        if code.count(needle) != 1:
            raise RuntimeError("recoverable loop could not locate the canonical action boundary")
        return cast(str, code.replace(needle, replacement))


class RecoveryCoordinator:
    """Own atomic attempt custody and replay for one stable run identity."""

    def __init__(
        self,
        *,
        run_id: str,
        target_attempts: int,
        checkpoint_path: Path,
        status_path: Path,
        fail_after_settlement_ordinal: int | None = None,
        fail_during_action_ordinal: int | None = None,
    ) -> None:
        self.run_id = run_id
        self.target_attempts = int(target_attempts)
        self.checkpoint_path = checkpoint_path
        self.status_path = status_path
        self.fail_after_settlement_ordinal = fail_after_settlement_ordinal
        self.fail_during_action_ordinal = fail_during_action_ordinal
        self._call_ordinal = 0
        self._world: RecoverableLoopWorld | None = None
        self._original_syscall: Syscall | None = None
        self._active_attempt_ordinal: int | None = None
        self._checkpoint = self._load_or_create()

    def _new_checkpoint(self) -> RecoveryCheckpointV1:
        return RecoveryCheckpointV1(
            run_id=self.run_id,
            target_attempts=self.target_attempts,
            updated_at=_now(),
        )

    def _load_or_create(self) -> RecoveryCheckpointV1:
        if not self.checkpoint_path.exists():
            checkpoint = self._new_checkpoint()
            _atomic_write_json(self.checkpoint_path, checkpoint.model_dump(mode="json"))
            return checkpoint
        try:
            raw = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
            checkpoint = cast(RecoveryCheckpointV1, RecoveryCheckpointV1.model_validate(raw))
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            self._write_invalid_status(f"corrupt checkpoint: {type(exc).__name__}: {exc}")
            raise RecoveryTerminalError("corrupt recovery checkpoint") from exc
        if checkpoint.run_id != self.run_id or checkpoint.target_attempts != self.target_attempts:
            self._write_invalid_status("checkpoint identity or target does not match the requested run")
            raise RecoveryTerminalError("recovery checkpoint identity mismatch")
        if checkpoint.terminal_state == "invalid":
            self._write_status("invalid", terminal_reason=checkpoint.terminal_reason)
            raise RecoveryTerminalError(checkpoint.terminal_reason or "recovery checkpoint is invalid")
        unsafe = next(
            (
                attempt
                for attempt in checkpoint.attempts
                if attempt.phase in {"dispatching", "applying", "dispatch_ambiguous", "invalid"}
            ),
            None,
        )
        if unsafe is not None:
            reason = f"attempt {unsafe.attempt_id} stopped in unsafe phase {unsafe.phase}"
            checkpoint.terminal_state = "invalid"
            checkpoint.terminal_reason = reason
            checkpoint.updated_at = _now()
            _atomic_write_json(self.checkpoint_path, checkpoint.model_dump(mode="json"))
            self._write_status("invalid", checkpoint=checkpoint, terminal_reason=reason)
            raise RecoveryTerminalError(reason)
        return checkpoint

    def _write_invalid_status(self, reason: str) -> None:
        payload = RecoveryStatusV1(
            run_id=self.run_id,
            lifecycle_state="invalid",
            target_attempts=self.target_attempts,
            committed_attempts=0,
            provider_dispatch_count=0,
            last_attempt_id=None,
            last_attempt_phase="invalid",
            terminal_reason=reason,
            heartbeat_at=_now(),
        )
        _atomic_write_json(self.status_path, payload.model_dump(mode="json"))

    def _persist(self) -> None:
        self._checkpoint.updated_at = _now()
        _atomic_write_json(self.checkpoint_path, self._checkpoint.model_dump(mode="json"))

    def _write_status(
        self,
        lifecycle_state: Literal["ready", "running", "paused", "completed", "stopped", "invalid"],
        *,
        checkpoint: RecoveryCheckpointV1 | None = None,
        terminal_reason: str | None = None,
        pid: int | None = None,
    ) -> None:
        current = checkpoint or self._checkpoint
        attempts = current.attempts
        last = attempts[-1] if attempts else None
        payload = RecoveryStatusV1(
            run_id=self.run_id,
            lifecycle_state=lifecycle_state,
            target_attempts=self.target_attempts,
            committed_attempts=sum(item.phase == "committed" for item in attempts),
            provider_dispatch_count=current.provider_dispatch_count,
            last_attempt_id=last.attempt_id if last is not None else None,
            last_attempt_phase=last.phase if last is not None else None,
            terminal_reason=terminal_reason or current.terminal_reason,
            pid=pid,
            heartbeat_at=_now(),
        )
        _atomic_write_json(self.status_path, payload.model_dump(mode="json"))

    def publish_status(
        self,
        lifecycle_state: Literal["ready", "running", "paused", "completed", "stopped", "invalid"],
        *,
        terminal_reason: str | None = None,
        pid: int | None = None,
    ) -> None:
        self._write_status(lifecycle_state, terminal_reason=terminal_reason, pid=pid)

    def status(self) -> dict[str, Any]:
        if self.status_path.exists():
            try:
                return cast(dict[str, Any], json.loads(self.status_path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                pass
        attempts = self._checkpoint.attempts
        last = attempts[-1] if attempts else None
        return {
            "schema_version": "ae3_recovery_status.v1",
            "run_id": self.run_id,
            "lifecycle_state": "ready",
            "target_attempts": self.target_attempts,
            "committed_attempts": sum(item.phase == "committed" for item in attempts),
            "provider_dispatch_count": self._checkpoint.provider_dispatch_count,
            "last_attempt_id": last.attempt_id if last else None,
            "last_attempt_phase": last.phase if last else None,
            "terminal_reason": self._checkpoint.terminal_reason,
            "pid": None,
            "heartbeat_at": _now(),
        }

    def attach(self, world: RecoverableLoopWorld) -> None:
        self._world = world
        self._original_syscall = cast(Syscall, world.call_llm_as_syscall_async)
        world.call_llm_as_syscall_async = self.call_llm  # type: ignore[method-assign]
        target = cast(Any, world)
        target._recovery_mark_applying = self.mark_applying
        target._recovery_mark_committed = self.mark_committed

    def _replay_settlement(
        self,
        *,
        attempt: RecoverableAttemptV1,
        payer_id: str,
        model: str,
        messages: list[dict[str, Any]],
    ) -> None:
        if self._world is None or attempt.syscall_result is None:
            self._invalidate(attempt, "replay cannot reconstruct settlement without a world and result")
        prepared, context = self._world._prepare_llm_syscall(
            payer_id=payer_id,
            model=model,
            messages=messages,
        )
        if prepared is not None or context is None:
            self._invalidate(attempt, f"replay settlement preflight failed: {prepared}")
        result = attempt.syscall_result
        if context.trace_id != attempt.trace_id:
            self._invalidate(
                attempt,
                f"replay trace drift: expected {attempt.trace_id}, observed {context.trace_id}",
            )
        usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
        codex_types = result.get("codex_event_types")
        codex_events = (
            [{"type": str(item)} for item in codex_types]
            if isinstance(codex_types, list)
            else []
        )
        llm_result = SimpleNamespace(
            content=result.get("content") or "",
            tool_calls=result.get("tool_calls") or [],
            usage=usage,
            cache_hit=bool(result.get("cache_hit", False)),
            marginal_cost=float(result.get("cost", 0.0) or 0.0),
            cost=float(result.get("cost", 0.0) or 0.0),
            cost_source=str(result.get("cost_source", "replayed")),
            billing_mode=str(result.get("billing_mode", "unknown")),
            codex_events=codex_events,
        )
        structured_action = result.get("structured_action")
        self._world._settle_llm_syscall(
            context,
            llm_result,
            structured_action=(
                cast(dict[str, Any], structured_action)
                if isinstance(structured_action, dict)
                else None
            ),
            structured_schema_sha256=(
                str(result.get("structured_schema_sha256"))
                if result.get("structured_schema_sha256")
                else None
            ),
            settled_error=(
                RuntimeError(str(result.get("error") or "settled provider rejection"))
                if result.get("success") is False
                else None
            ),
            settled_error_code=(
                str(result.get("error_code")) if result.get("error_code") else None
            ),
        )

    def _attempt_for_trace(self, trace_id: str | None) -> RecoverableAttemptV1 | None:
        if not trace_id:
            return None
        return next((item for item in self._checkpoint.attempts if item.trace_id == trace_id), None)

    async def call_llm(
        self,
        *,
        payer_id: str,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self._call_ordinal += 1
        ordinal = self._call_ordinal
        request = {
            "payer_id": payer_id,
            "model": model,
            "messages": messages,
            "tools": tools or [],
        }
        request_sha256 = _request_sha256(request)
        attempt_id = f"{self.run_id}/attempt_{ordinal:02d}"

        if ordinal <= len(self._checkpoint.attempts):
            attempt = self._checkpoint.attempts[ordinal - 1]
            if (
                attempt.attempt_id != attempt_id
                or attempt.request_sha256 != request_sha256
                or attempt.payer_id != payer_id
                or attempt.model != model
            ):
                attempt.replay_observed_request = cast(
                    dict[str, Any], json.loads(json.dumps(request, ensure_ascii=True))
                )
                reason = f"replay request drift at {attempt_id}"
                self._invalidate(attempt, reason)
            if attempt.phase not in {"provider_settled", "committed"} or attempt.syscall_result is None:
                self._invalidate(attempt, f"attempt cannot replay from phase {attempt.phase}")
            self._active_attempt_ordinal = ordinal
            self._replay_settlement(
                attempt=attempt,
                payer_id=payer_id,
                model=model,
                messages=messages,
            )
            if self._world is not None:
                self._world.logger.log(
                    "llm_syscall_replayed",
                    {
                        "event_number": self._world.event_number,
                        "trace_id": attempt.trace_id,
                        "attempt_id": attempt.attempt_id,
                        "payer_id": payer_id,
                        "model": model,
                    },
                )
            return dict(attempt.syscall_result)

        if ordinal != len(self._checkpoint.attempts) + 1:
            raise RecoveryTerminalError("attempt journal ordinal gap")
        attempt = RecoverableAttemptV1(
            ordinal=ordinal,
            attempt_id=attempt_id,
            request_sha256=request_sha256,
            payer_id=payer_id,
            model=model,
            request=cast(dict[str, Any], json.loads(json.dumps(request, ensure_ascii=True))),
            phase="dispatching",
        )
        self._checkpoint.attempts.append(attempt)
        self._checkpoint.provider_dispatch_count += 1
        self._active_attempt_ordinal = ordinal
        self._persist()

        if self._original_syscall is None:
            self._invalidate(attempt, "recovery coordinator has no provider syscall")
        try:
            result = await self._original_syscall(
                payer_id=payer_id,
                model=model,
                messages=messages,
                tools=tools,
            )
        except BaseException as exc:
            attempt.phase = "dispatch_ambiguous"
            attempt.error = f"{type(exc).__name__}: {exc}"
            self._checkpoint.terminal_state = "invalid"
            self._checkpoint.terminal_reason = attempt.error
            self._persist()
            self._write_status("invalid", terminal_reason=attempt.error)
            raise RecoveryTerminalError(attempt.error) from exc

        attempt.trace_id = str(result.get("trace_id") or "") or None
        attempt.syscall_result = cast(dict[str, Any], json.loads(json.dumps(result, ensure_ascii=True)))
        if result.get("error_code") == "llm_dispatch_ambiguous":
            attempt.phase = "dispatch_ambiguous"
            attempt.error = str(result.get("error") or "provider dispatch is ambiguous")
            self._checkpoint.terminal_state = "invalid"
            self._checkpoint.terminal_reason = attempt.error
            self._persist()
            self._write_status("invalid", terminal_reason=attempt.error)
            raise RecoveryTerminalError(attempt.error)
        attempt.phase = "provider_settled"
        self._persist()
        self._write_status("running", pid=os.getpid())
        if self.fail_after_settlement_ordinal == ordinal:
            raise SimulatedRecoveryInterruption(f"injected after settlement for {attempt_id}")
        return result

    def _invalidate(self, attempt: RecoverableAttemptV1, reason: str) -> NoReturn:
        attempt.phase = "invalid"
        attempt.error = reason
        self._checkpoint.terminal_state = "invalid"
        self._checkpoint.terminal_reason = reason
        self._persist()
        self._write_status("invalid", terminal_reason=reason)
        raise RecoveryTerminalError(reason)

    def mark_applying(self, trace_id: str | None) -> None:
        attempt = self._attempt_for_trace(trace_id)
        if attempt is None or attempt.phase == "committed":
            return
        if attempt.phase != "provider_settled":
            self._invalidate(attempt, f"cannot apply attempt from phase {attempt.phase}")
        attempt.phase = "applying"
        self._persist()
        if self.fail_during_action_ordinal == attempt.ordinal:
            raise SimulatedRecoveryInterruption(
                f"injected during action application for {attempt.attempt_id}"
            )

    def mark_committed(self, trace_id: str | None) -> None:
        attempt = self._attempt_for_trace(trace_id)
        if attempt is None or attempt.phase == "committed":
            return
        if attempt.phase != "applying":
            self._invalidate(attempt, f"cannot commit attempt from phase {attempt.phase}")
        attempt.phase = "committed"
        self._persist()
        committed = sum(item.phase == "committed" for item in self._checkpoint.attempts)
        lifecycle: Literal["completed", "running"] = (
            "completed" if committed >= self.target_attempts else "running"
        )
        self._write_status(lifecycle, pid=os.getpid())


def build_recoverable_world(
    config: AppConfig,
    *,
    run_id: str,
    target_attempts: int,
    checkpoint_path: Path,
    status_path: Path,
    fail_after_settlement_ordinal: int | None = None,
    fail_during_action_ordinal: int | None = None,
) -> tuple[RecoverableLoopWorld, RecoveryCoordinator]:
    """Construct one deterministic world and attach its recovery coordinator."""

    coordinator = RecoveryCoordinator(
        run_id=run_id,
        target_attempts=target_attempts,
        checkpoint_path=checkpoint_path,
        status_path=status_path,
        fail_after_settlement_ordinal=fail_after_settlement_ordinal,
        fail_during_action_ordinal=fail_during_action_ordinal,
    )
    world = RecoverableLoopWorld(config, run_id=run_id)
    coordinator.attach(world)
    return world, coordinator
