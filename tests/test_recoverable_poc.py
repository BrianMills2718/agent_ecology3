from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from agent_ecology3.config import AppConfig
from agent_ecology3.dashboard import create_app
from agent_ecology3.simulation import (
    RecoveryCoordinator,
    RecoveryScarcityBoundary,
    RecoveryTerminalError,
    SimulatedRecoveryInterruption,
    SimulationRunner,
    build_recoverable_world,
)


def _config(tmp_path: Path) -> AppConfig:
    config = AppConfig()
    config.principals.count = 1
    config.principals.id_prefix = "alpha_"
    config.principals.starting_llm_budget = 10.0
    config.llm.enable_bootstrap_loop_llm = True
    config.llm.loop_forced_explore_mode = "off"
    config.llm.loop_llm_cooldown_seconds = 0.0
    config.simulation.loop.min_delay_seconds = 0.001
    config.simulation.loop.max_delay_seconds = 0.002
    config.simulation.summary_interval_seconds = 30
    config.logging.logs_dir = str(tmp_path / "logs")
    config.logging.recent_event_limit = 2000
    config.mint.enabled = False
    return config


def _paths(tmp_path: Path) -> tuple[Path, Path]:
    custody = tmp_path / "custody"
    return custody / "checkpoint.json", custody / "status.json"


def _fake_provider(world, dispatches: list[str]):
    async def call(*, payer_id, model, messages, tools=None):
        prepared, context = world._prepare_llm_syscall(
            payer_id=payer_id,
            model=model,
            messages=messages,
        )
        assert prepared is None
        assert context is not None
        trace_id = context.trace_id
        dispatches.append(trace_id)
        action = {
            "action_type": "query_kernel",
            "query_type": "resources",
            "params": {},
        }
        return world._settle_llm_syscall(
            context,
            SimpleNamespace(
                content="",
                tool_calls=[],
                usage={"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
                cache_hit=False,
                marginal_cost=0.0,
                cost=0.0,
                cost_source="fixture",
                billing_mode="subscription_included",
                codex_events=[{"type": "agent_message"}],
            ),
            structured_action=action,
            structured_schema_sha256="fixture",
        )

    return call


def test_settled_attempt_replays_without_replacement_dispatch(tmp_path: Path) -> None:
    config = _config(tmp_path)
    checkpoint, status = _paths(tmp_path)
    dispatches: list[str] = []
    world, coordinator = build_recoverable_world(
        config,
        run_id="plan10_recovery_fixture",
        target_attempts=16,
        checkpoint_path=checkpoint,
        status_path=status,
        fail_after_settlement_ordinal=8,
    )
    coordinator._original_syscall = _fake_provider(world, dispatches)

    with pytest.raises(SimulatedRecoveryInterruption):
        asyncio.run(SimulationRunner(world).run(duration=5, target_llm_attempts=16))

    interrupted = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert len(dispatches) == 8
    assert interrupted["attempts"][-1]["phase"] == "provider_settled"

    replay_world, replay = build_recoverable_world(
        config,
        run_id="plan10_recovery_fixture",
        target_attempts=16,
        checkpoint_path=checkpoint,
        status_path=status,
    )
    replay._original_syscall = _fake_provider(replay_world, dispatches)
    asyncio.run(SimulationRunner(replay_world).run(duration=5, target_llm_attempts=16))

    completed = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert len(dispatches) == 16
    assert completed["provider_dispatch_count"] == 16
    assert len(completed["attempts"]) == 16
    assert all(item["phase"] == "committed" for item in completed["attempts"])
    assert json.loads(status.read_text(encoding="utf-8"))["lifecycle_state"] == "completed"


def test_interrupted_action_application_is_terminal(tmp_path: Path) -> None:
    config = _config(tmp_path)
    checkpoint, status = _paths(tmp_path)
    dispatches: list[str] = []
    world, coordinator = build_recoverable_world(
        config,
        run_id="plan10_action_interruption",
        target_attempts=2,
        checkpoint_path=checkpoint,
        status_path=status,
        fail_during_action_ordinal=1,
    )
    coordinator._original_syscall = _fake_provider(world, dispatches)

    with pytest.raises(SimulatedRecoveryInterruption):
        asyncio.run(SimulationRunner(world).run(duration=2, target_llm_attempts=2))
    assert len(dispatches) == 1

    with pytest.raises(RecoveryTerminalError):
        RecoveryCoordinator(
            run_id="plan10_action_interruption",
            target_attempts=2,
            checkpoint_path=checkpoint,
            status_path=status,
        )
    assert len(dispatches) == 1
    durable = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert durable["terminal_state"] == "invalid"
    assert "unsafe phase applying" in durable["terminal_reason"]


def test_corrupt_checkpoint_is_terminal_without_dispatch(tmp_path: Path) -> None:
    checkpoint, status = _paths(tmp_path)
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text("{not-json", encoding="utf-8")

    with pytest.raises(RecoveryTerminalError):
        RecoveryCoordinator(
            run_id="plan10_corrupt",
            target_attempts=2,
            checkpoint_path=checkpoint,
            status_path=status,
        )

    payload = json.loads(status.read_text(encoding="utf-8"))
    assert payload["lifecycle_state"] == "invalid"
    assert "corrupt checkpoint" in payload["terminal_reason"]


def test_pre_dispatch_budget_rejection_stops_without_provider_dispatch(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    checkpoint, status = _paths(tmp_path)
    _world, coordinator = build_recoverable_world(
        config,
        run_id="plan11_scarcity_fixture",
        target_attempts=16,
        checkpoint_path=checkpoint,
        status_path=status,
    )

    async def reject_before_dispatch(**_kwargs):
        return {
            "success": False,
            "error": "insufficient llm_budget",
            "error_code": "insufficient_budget",
            "budget": 0.001,
            "estimated_cost": 0.004,
        }

    coordinator._original_syscall = reject_before_dispatch
    with pytest.raises(RecoveryScarcityBoundary, match="scarcity_binding"):
        asyncio.run(
            coordinator.call_llm(
                payer_id="alpha_1",
                model=config.llm.default_model,
                messages=[{"role": "user", "content": "decide"}],
            )
        )

    durable = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert durable["provider_dispatch_count"] == 0
    assert durable["terminal_state"] == "stopped"
    assert durable["attempts"][-1]["phase"] == "pre_dispatch_rejected"
    assert durable["attempts"][-1]["trace_id"] is None
    assert json.loads(status.read_text(encoding="utf-8"))["lifecycle_state"] == "stopped"


def test_runner_can_start_paused_and_resume(tmp_path: Path) -> None:
    async def exercise() -> None:
        config = _config(tmp_path)
        config.llm.enable_bootstrap_loop_llm = False
        world, _coordinator = build_recoverable_world(
            config,
            run_id="plan10_paused",
            target_attempts=1,
            checkpoint_path=_paths(tmp_path)[0],
            status_path=_paths(tmp_path)[1],
        )
        runner = SimulationRunner(world)
        task = asyncio.create_task(runner.run(duration=0.2, start_paused=True))
        await asyncio.sleep(0.03)
        assert runner.is_paused is True
        assert world.event_number == 0
        runner.resume()
        await task
        assert world.event_number > 0

    asyncio.run(exercise())


def test_dashboard_preserves_controls_and_exposes_recovery_state(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.llm.enable_bootstrap_loop_llm = False
    world, coordinator = build_recoverable_world(
        config,
        run_id="plan10_dashboard_fixture",
        target_attempts=2,
        checkpoint_path=_paths(tmp_path)[0],
        status_path=_paths(tmp_path)[1],
    )
    runner = SimulationRunner(world)
    coordinator.publish_status("paused", pid=123)
    app = create_app(
        world_provider=lambda: world,
        runner_provider=lambda: runner,
        recovery_provider=coordinator.status,
    )

    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "Luna attempts" in page.text
        state = client.get("/state").json()
        assert state["run_id"] == "plan10_dashboard_fixture"
        assert state["recovery"]["target_attempts"] == 2
        assert state["recovery"]["lifecycle_state"] == "paused"
        assert client.post("/control/pause").json()["success"] is True
        assert runner.is_paused is True
        assert client.post("/control/resume").json()["success"] is True
        assert runner.is_paused is False
        assert client.post("/control/stop").json()["success"] is True


def test_detached_status_fails_loud_when_no_worker_exists(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_recoverable_evaluation.py"
    completed = subprocess.run(
        [sys.executable, str(script), "status", "--data-dir", str(tmp_path / "missing")],
        cwd=script.parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert payload["worker_alive"] is False
    assert payload["error"] == "no durable status"
