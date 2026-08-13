from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from agent_ecology3.analysis.behavioral_feasibility_repair import (
    validate_cell_evidence,
    validate_design_file,
)
from agent_ecology3.analysis.hard_call_cap import validate_capped_cell
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
from scripts.run_recoverable_evaluation import _configure, _validate_start_contract
from scripts.run_recoverable_evaluation import _write_receipt as write_run_receipt


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


def test_dashboard_reopens_completed_pair_read_only(tmp_path: Path) -> None:
    review_runs: dict[str, Path] = {}
    for condition, lifecycle in (("prescribed", "completed"), ("minimal", "stopped")):
        data_dir = tmp_path / condition
        log_path = data_dir / "events.jsonl"
        data_dir.mkdir(parents=True)
        log_path.write_text(
            json.dumps(
                {
                    "event_type": "loop_decision",
                    "event_number": 14,
                    "principal_id": "alpha_2",
                    "decision_action": "write_artifact",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        receipt = {
            "acknowledgement": f"eval15/luna-medium/{condition}/pair-01/v1",
            "recovery": {
                "run_id": f"eval15_{condition}",
                "committed_attempts": 14,
                "target_attempts": 14,
                "lifecycle_state": lifecycle,
            },
            "world_state": {
                "run_id": f"eval15_{condition}",
                "event_number": 14,
                "principal_count": 2,
                "artifact_count": 8,
                "events": [],
                "log_path": str(log_path),
            },
        }
        (data_dir / "run_receipt.json").write_text(
            json.dumps(receipt), encoding="utf-8"
        )
        review_runs[condition] = data_dir

    app = create_app(review_runs=review_runs)
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "Review run" in page.text
        assert "review only" in page.text

        runs = client.get("/runs").json()
        assert [item["id"] for item in runs["runs"]] == ["prescribed", "minimal"]
        assert runs["read_only"] is True

        minimal = client.get("/state?run=minimal").json()
        assert minimal["run_id"] == "eval15_minimal"
        assert minimal["review"] == {
            "read_only": True,
            "run": "minimal",
            "acknowledgement": "eval15/luna-medium/minimal/pair-01/v1",
        }
        assert minimal["recovery"]["lifecycle_state"] == "stopped"

        events = client.get("/events?run=minimal&limit=10").json()
        assert events["count"] == 1
        assert events["events"][0]["decision_action"] == "write_artifact"
        assert client.post("/control/resume").json() == {
            "success": False,
            "error": "runner unavailable",
        }


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


def test_control_acknowledgement_freezes_budget_and_horizon() -> None:
    valid = SimpleNamespace(
        acknowledgement="plan11/luna-medium/scarcity-control/v1",
        target_attempts=8,
        starting_llm_budget=0.066384,
    )
    _validate_start_contract(valid)

    for attempts, budget in ((7, 0.066384), (8, 0.033192), (9, 0.066384)):
        invalid = SimpleNamespace(
            acknowledgement="plan11/luna-medium/scarcity-control/v1",
            target_attempts=attempts,
            starting_llm_budget=budget,
        )
        with pytest.raises(RuntimeError, match="control requires exactly 8"):
            _validate_start_contract(invalid)


@pytest.mark.parametrize(
    ("mode", "acknowledgement"),
    [
        ("prescribed", "eval12/luna-medium/prescribed/pair-01/v1"),
        ("minimal", "eval12/luna-medium/minimal/pair-01/v1"),
    ],
)
def test_eval12_acknowledgements_freeze_matched_cell(
    mode: str, acknowledgement: str
) -> None:
    valid = SimpleNamespace(
        acknowledgement=acknowledgement,
        target_attempts=16,
        starting_llm_budget=0.033192,
        principal_count=2,
        cognition_mode=mode,
        policy_seed=24120,
    )
    _validate_start_contract(valid)

    invalid = SimpleNamespace(**{**vars(valid), "principal_count": 1})
    with pytest.raises(RuntimeError, match="Evaluation 12 requires exactly 16"):
        _validate_start_contract(invalid)

    crossed = SimpleNamespace(
        **{
            **vars(valid),
            "acknowledgement": "eval12/luna-medium/minimal/pair-01/v1"
            if mode == "prescribed"
            else "eval12/luna-medium/prescribed/pair-01/v1",
        }
    )
    with pytest.raises(RuntimeError, match="exact Plan 10, Plan 11, or Evaluation 12"):
        _validate_start_contract(crossed)


def test_receipt_snapshots_terminal_status_published_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    world, coordinator = build_recoverable_world(
        config,
        run_id="terminal_receipt_fixture",
        target_attempts=2,
        checkpoint_path=_paths(tmp_path)[0],
        status_path=_paths(tmp_path)[1],
    )
    coordinator.publish_status("stopped", terminal_reason="fixture_stop", pid=123)
    monkeypatch.setattr(
        "llm_client.get_llm_call_receipts", lambda **_kwargs: []
    )

    data_dir = tmp_path / "custody"
    write_run_receipt(
        data_dir=data_dir,
        coordinator=coordinator,
        world=world,
        source={"agent_ecology3_revision": "fixture"},
        acknowledgement="fixture",
    )

    receipt = json.loads((data_dir / "run_receipt.json").read_text(encoding="utf-8"))
    assert receipt["recovery"]["lifecycle_state"] == "stopped"
    assert receipt["recovery"]["terminal_reason"] == "fixture_stop"


def test_eval14_provider_free_contract_and_runtime_projection(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = validate_design_file(
        repo_root / "config/evaluations/14_luna_behavioral_feasibility.json"
    )
    assert result["status"] == "pass"
    assert result["provider_calls"] == 0

    config = _configure(
        repo_root / "config/config.yaml",
        tmp_path,
        starting_llm_budget=0.033192,
        principal_count=2,
        cognition_mode="prescribed",
        policy_seed=24140,
        action_failure_policy="fail_closed_no_substitute",
        mint_enabled=True,
        mint_auction_after_horizon=True,
    )
    assert config.llm.loop_action_failure_policy == "fail_closed_no_substitute"
    assert config.mint.enabled is True
    assert config.mint.scoring_max_budget == 0.0
    assert config.mint.first_auction_delay_seconds > config.simulation.default_duration_seconds


@pytest.mark.parametrize("mode", ["prescribed", "minimal"])
def test_eval14_acknowledgement_freezes_authorized_cell(mode: str) -> None:
    args = SimpleNamespace(
        acknowledgement=f"eval14/luna-medium/{mode}/pair-01/v1",
        target_attempts=15,
        starting_llm_budget=0.033192,
        principal_count=2,
        cognition_mode=mode,
        policy_seed=24140,
    )
    _validate_start_contract(args)

    with pytest.raises(RuntimeError, match="requires exactly 15 attempt records"):
        _validate_start_contract(SimpleNamespace(**{**vars(args), "target_attempts": 14}))


def test_eval14_cell_validator_suppresses_invalid_pair() -> None:
    committed = [
        {
            "ordinal": ordinal,
            "phase": "committed",
            "payer_id": f"alpha_{1 if ordinal % 2 else 2}",
            "trace_id": f"trace-{ordinal}",
        }
        for ordinal in range(1, 15)
    ]
    boundary = {
        "ordinal": 15,
        "phase": "pre_dispatch_rejected",
        "payer_id": "alpha_1",
        "trace_id": None,
    }
    checkpoint = {
        "attempts": [*committed, boundary],
        "provider_dispatch_count": 14,
        "terminal_reason": "scarcity_binding_pre_dispatch",
    }
    status = {
        "lifecycle_state": "stopped",
        "terminal_reason": "scarcity_binding_pre_dispatch",
    }
    receipt = {
        "acknowledgement": "eval14/luna-medium/prescribed/pair-01/v1",
        "recovery": status,
        "checkpoint": checkpoint,
        "shared_client_receipts": [{} for _ in range(14)],
        "local_action_failure_policy": "fail_closed_no_substitute",
        "mint": {
            "enabled": True,
            "first_auction_delay_seconds": 3601.0,
            "scoring_max_budget": 0.0,
        },
    }
    valid = validate_cell_evidence(
        condition="prescribed",
        checkpoint=checkpoint,
        status=status,
        receipt=receipt,
    )
    assert valid["status"] == "valid"

    invalid = validate_cell_evidence(
        condition="prescribed",
        checkpoint={**checkpoint, "provider_dispatch_count": 15},
        status=status,
        receipt=receipt,
    )
    assert invalid["status"] == "invalid"
    assert invalid["failed_checks"] == ["dispatch_ceiling"]


@pytest.mark.parametrize("mode", ["prescribed", "minimal"])
def test_eval15_acknowledgement_freezes_hard_call_cap(mode: str) -> None:
    args = SimpleNamespace(
        acknowledgement=f"eval15/luna-medium/{mode}/pair-01/v1",
        target_attempts=14,
        starting_llm_budget=0.033192,
        principal_count=2,
        cognition_mode=mode,
        policy_seed=24150,
    )
    _validate_start_contract(args)

    with pytest.raises(RuntimeError, match="requires exactly 14 attempts"):
        _validate_start_contract(SimpleNamespace(**{**vars(args), "target_attempts": 15}))


def test_eval15_validator_rejects_fifteenth_dispatch() -> None:
    attempts = [
        {
            "ordinal": ordinal,
            "phase": "committed",
            "payer_id": f"alpha_{1 if ordinal % 2 else 2}",
            "trace_id": f"trace-{ordinal}",
        }
        for ordinal in range(1, 15)
    ]
    checkpoint = {
        "attempts": attempts,
        "provider_dispatch_count": 14,
        "terminal_state": None,
        "terminal_reason": None,
    }
    status = {"lifecycle_state": "completed", "terminal_reason": None}
    receipt = {
        "acknowledgement": "eval15/luna-medium/prescribed/pair-01/v1",
        "recovery": status,
        "checkpoint": checkpoint,
        "shared_client_receipts": [{} for _ in range(14)],
        "local_action_failure_policy": "fail_closed_no_substitute",
        "mint": {"enabled": True, "scoring_max_budget": 0.0},
    }
    valid = validate_capped_cell(
        condition="prescribed",
        checkpoint=checkpoint,
        status=status,
        receipt=receipt,
    )
    assert valid["status"] == "valid"

    stopped_status = {"lifecycle_state": "stopped", "terminal_reason": None}
    stopped_receipt = {**receipt, "recovery": stopped_status}
    stopped = validate_capped_cell(
        condition="prescribed",
        checkpoint=checkpoint,
        status=stopped_status,
        receipt=stopped_receipt,
    )
    assert stopped["status"] == "valid"

    attempt_15 = {
        "ordinal": 15,
        "phase": "committed",
        "payer_id": "alpha_1",
        "trace_id": "trace-15",
    }
    invalid_checkpoint = {
        **checkpoint,
        "attempts": [*attempts, attempt_15],
        "provider_dispatch_count": 15,
    }
    invalid = validate_capped_cell(
        condition="prescribed",
        checkpoint=invalid_checkpoint,
        status=status,
        receipt=receipt,
    )
    assert invalid["status"] == "invalid"
    assert "hard_fourteen_call_cap" in invalid["failed_checks"]
