from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
import scripts.run_recoverable_evaluation as recoverable_script

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
from scripts.run_recoverable_evaluation import (
    PLAN19_ACKNOWLEDGEMENT,
    PLAN22_CANARY_ACKNOWLEDGEMENT,
    _configure,
    _dashboard_launch_profile,
    _discover_review_runs,
    _launch_dashboard_run,
    _seed_mvp_opportunities,
    _terminal_lifecycle,
    _validate_start_contract,
)
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


def _fake_economic_provider(world, dispatches: list[str]):
    """Exercise the real structured-action path without a provider call."""

    async def call(*, payer_id, model, messages, tools=None):
        prepared, context = world._prepare_llm_syscall(
            payer_id=payer_id,
            model=model,
            messages=messages,
        )
        assert prepared is None
        assert context is not None
        dispatches.append(context.trace_id)
        action = (
            {
                "action_type": "query_kernel",
                "query_type": "artifacts",
                "params": {"readable_only": True},
            }
            if payer_id == "alpha_1"
            else {
                "action_type": "read_artifact",
                "artifact_id": "alpha_1_market_signal",
            }
        )
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


def test_local_pre_dispatch_failure_is_terminal_without_substitute(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    config.llm.loop_action_failure_policy = "fail_closed_no_substitute"
    checkpoint, status = _paths(tmp_path)
    _world, coordinator = build_recoverable_world(
        config,
        run_id="plan22_pre_dispatch_failure",
        target_attempts=14,
        checkpoint_path=checkpoint,
        status_path=status,
    )

    async def fail_before_dispatch(**_kwargs):
        return {
            "success": False,
            "trace_id": "ae3/plan22/pre-dispatch",
            "error": "llm call failed: cwd was deleted",
            "error_code": "llm_error",
            "settlement_status": "pre_dispatch_failed",
            "reservation_retained": False,
            "provider_dispatch_confirmed": False,
        }

    coordinator._original_syscall = fail_before_dispatch
    with pytest.raises(RecoveryTerminalError, match="cwd was deleted"):
        asyncio.run(
            coordinator.call_llm(
                payer_id="alpha_1",
                model=config.llm.default_model,
                messages=[{"role": "user", "content": "decide"}],
            )
        )

    durable = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert durable["provider_dispatch_count"] == 0
    assert durable["terminal_state"] == "invalid"
    assert durable["attempts"][-1]["phase"] == "invalid"
    assert json.loads(status.read_text(encoding="utf-8"))["lifecycle_state"] == "invalid"


def test_fail_closed_selected_action_failure_is_not_committed_or_replaced(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    config.principals.count = 2
    config.llm.loop_action_failure_policy = "fail_closed_no_substitute"
    checkpoint, status = _paths(tmp_path)
    dispatches: list[str] = []
    world, coordinator = build_recoverable_world(
        config,
        run_id="plan22_action_failure",
        target_attempts=1,
        checkpoint_path=checkpoint,
        status_path=status,
    )

    async def select_unauthorized_read(*, payer_id, model, messages, tools=None):
        prepared, context = world._prepare_llm_syscall(
            payer_id=payer_id,
            model=model,
            messages=messages,
        )
        assert prepared is None and context is not None
        dispatches.append(context.trace_id)
        return world._settle_llm_syscall(
            context,
            SimpleNamespace(
                content="",
                tool_calls=[],
                usage={"total_tokens": 10},
                cache_hit=False,
                marginal_cost=0.0,
                cost=0.0,
                cost_source="fixture",
                billing_mode="subscription_included",
                codex_events=[{"type": "agent_message"}],
            ),
            structured_action={
                "action_type": "read_artifact",
                "artifact_id": "alpha_2_strategy",
            },
            structured_schema_sha256="fixture",
        )

    coordinator._original_syscall = select_unauthorized_read
    with pytest.raises(RecoveryTerminalError, match="model-selected action failed"):
        asyncio.run(SimulationRunner(world).run(duration=2, target_llm_attempts=1))

    durable = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert len(dispatches) == 1
    assert durable["provider_dispatch_count"] == 1
    assert durable["terminal_state"] == "invalid"
    assert durable["attempts"][0]["phase"] == "invalid"
    assert not any(
        event.get("event_type") == "loop_decision"
        for event in world.logger.read_recent(100)
    )


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
        task = asyncio.create_task(runner.run(duration=0.05, start_paused=True))
        await asyncio.sleep(0.08)
        assert runner.is_paused is True
        assert world.event_number == 0
        assert runner.elapsed_seconds == pytest.approx(0.0, abs=0.01)
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
    world.logger.log(
        "loop_decision",
        {
            "event_number": 1,
            "principal_id": "alpha_1",
            "decision_action": "query_kernel",
            "decision": {
                "action_type": "query_kernel",
                "query_type": "resources",
                "params": {},
            },
            "result_success": True,
            "result_error_code": None,
            "fallback_used": True,
        },
    )
    shutdown_requested: list[bool] = []
    app = create_app(
        world_provider=lambda: world,
        runner_provider=lambda: runner,
        recovery_provider=coordinator.status,
        shutdown_provider=lambda: shutdown_requested.append(True),
    )

    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "Luna attempts" in page.text
        assert "substitute — not model-selected" in page.text
        state = client.get("/state").json()
        assert state["run_id"] == "plan10_dashboard_fixture"
        assert state["recovery"]["target_attempts"] == 2
        assert state["recovery"]["lifecycle_state"] == "paused"
        operator = client.get("/operator-state").json()
        assert operator["fallback_count"] == 1
        assert operator["actions"][0]["success"] is False
        assert operator["actions"][0]["local_action_success"] is True
        assert client.post("/control/pause").json()["success"] is True
        assert runner.is_paused is True
        assert client.post("/control/resume").json()["success"] is True
        assert runner.is_paused is False
        assert client.post("/control/stop").json()["success"] is True
        assert client.post("/control/shutdown").json() == {
            "success": True,
            "shutting_down": True,
        }
        assert shutdown_requested == [True]


def test_live_economic_vertical_is_discoverable_and_operator_visible(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    config.principals.count = 2
    config.llm.loop_action_failure_policy = "fail_closed_no_substitute"
    checkpoint, status = _paths(tmp_path)
    dispatches: list[str] = []
    world, coordinator = build_recoverable_world(
        config,
        run_id="plan19_provider_free_fixture",
        target_attempts=2,
        checkpoint_path=checkpoint,
        status_path=status,
    )
    assert _seed_mvp_opportunities(world) == [
        "alpha_1_market_signal",
        "alpha_2_validation_guide",
    ]

    discovery = world.execute_action_data(
        "alpha_2",
        {
            "action_type": "query_kernel",
            "query_type": "artifacts",
            "params": {"readable_only": True, "limit": 200},
        },
    )
    assert discovery.success
    opportunity = next(
        row
        for row in discovery.data["results"]
        if row["id"] == "alpha_1_market_signal"
    )
    assert opportunity["readable"] is True
    assert opportunity["read_price"] == 2
    assert not any(
        event.get("event_type") == "artifact_written"
        and event.get("artifact_id") in {
            "alpha_1_market_signal",
            "alpha_2_validation_guide",
        }
        for event in world.logger.read_recent(100)
    )

    coordinator._original_syscall = _fake_economic_provider(world, dispatches)
    asyncio.run(SimulationRunner(world).run(duration=2, target_llm_attempts=2))

    assert len(dispatches) == 2
    assert coordinator.status()["lifecycle_state"] == "completed"
    assert world.ledger.get_scrip("alpha_1") == 102
    assert world.ledger.get_scrip("alpha_2") == 98
    read_events = [
        event
        for event in world.logger.read_recent(200)
        if event.get("event_type") == "artifact_read"
        and event.get("artifact_id") == "alpha_1_market_signal"
    ]
    assert len(read_events) == 1
    assert read_events[0]["read_price_paid"] == 2
    assert read_events[0]["recipient"] == "alpha_1"

    app = create_app(
        world_provider=lambda: world,
        runner_provider=lambda: SimulationRunner(world),
        recovery_provider=coordinator.status,
    )
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "Live Luna Medium ecology" in page.text
        operator = client.get("/operator-state").json()
        assert operator["read_only"] is False
        assert operator["lifecycle_state"] == "completed"
        assert operator["max_turn"] == 2
        assert [agent["scrip"] for agent in operator["agents"]] == [102, 98]
        paid_action = next(
            action for action in operator["actions"] if action["action"] == "read_artifact"
        )
        assert paid_action["description"] == (
            "bought alpha_1_market_signal from alpha_1"
        )
        assert paid_action["value_amount"] == 2
        assert paid_action["value_unit"] == "scrip"
        assert paid_action["counterparty"] == "alpha_1"
        economic_artifacts = [
            artifact
            for artifact in operator["artifacts"]
            if artifact["scenario_opportunity"]
        ]
        assert len(economic_artifacts) == 2


def test_dashboard_reopens_completed_pair_read_only(tmp_path: Path) -> None:
    review_runs: dict[str, Path] = {}
    for condition, lifecycle in (("prescribed", "completed"), ("minimal", "stopped")):
        data_dir = tmp_path / condition
        log_path = data_dir / "events.jsonl"
        data_dir.mkdir(parents=True)
        action = "query_kernel" if condition == "prescribed" else "write_artifact"
        succeeded = condition == "minimal"
        log_events = [
            {
                "event_type": "loop_decision",
                "event_number": 14,
                "principal_id": "alpha_2",
                "decision_action": action,
                "decision": {
                    "action_type": action,
                    **(
                        {"artifact_id": "alpha_2_strategy_v2"}
                        if condition == "minimal"
                        else {"query_type": "artifacts"}
                    ),
                },
                "result_success": succeeded,
                "result_error_code": None if succeeded else "not_authorized",
                "fallback_used": False,
            }
        ]
        if condition == "minimal":
            log_events.append(
                {
                    "event_type": "artifact_written",
                    "event_number": 14,
                    "principal_id": "alpha_2",
                    "artifact_id": "alpha_2_strategy_v2",
                    "artifact_type": "strategy",
                    "was_update": False,
                }
            )
        log_path.write_text(
            "".join(json.dumps(event) + "\n" for event in log_events),
            encoding="utf-8",
        )
        receipt = {
            "acknowledgement": f"eval15/luna-medium/{condition}/pair-01/v1",
            "model": "codex/gpt-5.6-luna",
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
                "principals": ["alpha_1", "alpha_2"],
                "frozen": [],
                "balances": {
                    "alpha_1": {"scrip": 100, "resources": {"llm_budget": 0.01}},
                    "alpha_2": {"scrip": 100, "resources": {"llm_budget": 0.01}},
                },
                "quotas": {
                    "alpha_1": {"disk": {"used": 100, "quota": 1000}},
                    "alpha_2": {"disk": {"used": 120, "quota": 1000}},
                },
                "artifacts": [
                    {
                        "id": "alpha_2_strategy_v2",
                        "type": "strategy",
                        "owner": "alpha_2",
                        "created_by": "alpha_2",
                        "content": "Inspect the market before spending resources.",
                        "read_price": 0,
                        "invoke_price": 0,
                        "executable": False,
                        "access_contract_id": "kernel_contract_freeware",
                    }
                ]
                if condition == "minimal"
                else [],
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
        assert "Ecosystem" in page.text
        assert "Play run replay" in page.text
        assert "Agents" in page.text
        assert "Artifacts" in page.text
        assert "What happened, decision by decision" in page.text
        assert "Raw evidence" in page.text
        assert page.text.count("artifactScope').value = 'economy'") == 2

        runs = client.get("/runs").json()
        assert [item["id"] for item in runs["runs"]] == ["prescribed", "minimal"]
        assert runs["read_only"] is True
        assert runs["comparison_available"] is True

        summary = client.get("/review-summary").json()
        assert summary["valid_pair"] is True
        assert "not a causal result" in summary["scope_note"]
        assert [run["id"] for run in summary["runs"]] == ["prescribed", "minimal"]
        prescribed, minimal_summary = summary["runs"]
        assert prescribed["action_counts"] == {"query_kernel": 1}
        assert prescribed["failures"] == 1
        assert prescribed["fallbacks"] == 0
        assert minimal_summary["action_counts"] == {"write_artifact": 1}
        assert minimal_summary["artifacts_created"] == [
            {"id": "alpha_2_strategy_v2", "type": "strategy", "owner": "alpha_2"}
        ]
        assert minimal_summary["balances"][0]["scrip"] == 100

        operator = client.get("/operator-state?run=minimal").json()
        assert operator["schema_version"] == "ae3_operator_state.v1"
        assert operator["condition"] == "minimal"
        assert operator["max_turn"] == 1
        assert [agent["id"] for agent in operator["agents"]] == [
            "alpha_1",
            "alpha_2",
        ]
        assert operator["actions"][0] == {
            "turn": 1,
            "event_number": 14,
            "principal_id": "alpha_2",
            "action": "write_artifact",
            "description": "created alpha_2_strategy_v2",
            "artifact_id": "alpha_2_strategy_v2",
            "artifact_owner": "alpha_2",
            "success": True,
            "local_action_success": True,
            "error_code": None,
            "fallback_used": False,
            "value_amount": 0,
            "value_unit": None,
            "counterparty": None,
        }
        assert operator["artifacts"][0]["created_turn"] == 1
        assert operator["artifacts"][0]["agent_created"] is True
        assert operator["artifacts"][0]["content"].startswith("Inspect the market")

        minimal = client.get("/state?run=minimal").json()
        assert minimal["run_id"] == "eval15_minimal"
        assert minimal["review"] == {
            "read_only": True,
            "run": "minimal",
            "acknowledgement": "eval15/luna-medium/minimal/pair-01/v1",
        }
        assert minimal["recovery"]["lifecycle_state"] == "stopped"

        events = client.get("/events?run=minimal&limit=10").json()
        assert events["count"] == 2
        assert events["events"][0]["decision_action"] == "write_artifact"
        assert client.post("/control/resume").json() == {
            "success": False,
            "error": "runner unavailable",
        }


def test_dashboard_reopens_one_preserved_run_without_fabricating_pair(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "plan19_luna_live_economic_mvp_v1"
    data_dir.mkdir()
    log_path = data_dir / "events.jsonl"
    log_path.write_text(
        json.dumps(
            {
                "event_type": "loop_decision",
                "event_number": 14,
                "principal_id": "alpha_2",
                "decision_action": "read_artifact",
                "decision": {
                    "action_type": "read_artifact",
                    "artifact_id": "alpha_1_analysis",
                },
                "result_success": True,
                "read_price_paid": 2,
                "recipient": "alpha_1",
                "fallback_used": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    receipt = {
        "acknowledgement": "plan19/luna-medium/live-economic-mvp/v1",
        "model": "codex/gpt-5.6-luna",
        "recovery": {
            "run_id": data_dir.name,
            "committed_attempts": 14,
            "target_attempts": 14,
            "lifecycle_state": "completed",
        },
        "world_state": {
            "run_id": data_dir.name,
            "event_number": 14,
            "principal_count": 2,
            "artifact_count": 1,
            "principals": ["alpha_1", "alpha_2"],
            "frozen": [],
            "balances": {
                "alpha_1": {"scrip": 104, "resources": {"llm_budget": 0.0}},
                "alpha_2": {"scrip": 95, "resources": {"llm_budget": 0.0}},
            },
            "quotas": {},
            "artifacts": [
                {
                    "id": "alpha_1_analysis",
                    "type": "analysis",
                    "owner": "alpha_1",
                    "created_by": "alpha_1",
                    "content": "Reusable analysis",
                    "read_price": 2,
                    "invoke_price": 0,
                    "executable": False,
                    "access_contract_id": "kernel_contract_freeware",
                }
            ],
            "events": [],
            "log_path": str(log_path),
        },
    }
    (data_dir / "run_receipt.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )

    review_runs = _discover_review_runs(data_dir)
    assert review_runs == {data_dir.name: data_dir}
    app = create_app(review_runs=review_runs)
    with TestClient(app) as client:
        runs = client.get("/runs").json()
        assert runs == {
            "runs": [
                {
                    "id": data_dir.name,
                    "label": "Plan19 Luna Live Economic Mvp V1",
                }
            ],
            "default_run": data_dir.name,
            "read_only": True,
            "comparison_available": False,
            "launch_available": False,
        }
        assert client.get("/review-summary").json() == {
            "success": False,
            "error": "matched-pair comparison unavailable",
        }
        operator = client.get("/operator-state").json()
        assert operator["schema_version"] == "ae3_operator_state.v1"
        assert operator["read_only"] is True
        assert operator["lifecycle_state"] == "completed"
        assert operator["max_turn"] == 1
        assert [agent["scrip"] for agent in operator["agents"]] == [104, 95]
        assert operator["artifacts"][0]["id"] == "alpha_1_analysis"


def test_single_run_discovery_fails_loud_for_incomplete_custody(
    tmp_path: Path,
) -> None:
    (tmp_path / "run_receipt.json").write_text(
        json.dumps({"world_state": {}, "recovery": {}}), encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="has no event log"):
        _discover_review_runs(tmp_path)


def test_dashboard_launch_api_exposes_profile_and_visible_failure(
    tmp_path: Path,
) -> None:
    launches: list[bool] = []

    def launch() -> dict[str, object]:
        launches.append(True)
        return {
            "success": True,
            "url": "http://127.0.0.1:9021/",
            "status": {"lifecycle_state": "paused", "provider_dispatch_count": 0},
        }

    app = create_app(
        review_runs={"archived_run": tmp_path},
        launch_profile=_dashboard_launch_profile(),
        launch_provider=launch,
    )
    with TestClient(app) as client:
        page = client.get("/")
        assert "New paused run" in page.text
        assert "No Luna call happens until you press Resume" in page.text
        runs = client.get("/runs").json()
        assert runs["launch_available"] is True
        profile = client.get("/launch-profile").json()
        assert profile == {"success": True, "profile": _dashboard_launch_profile()}
        launched = client.post("/launch").json()
        assert launched["success"] is True
        assert launched["status"]["lifecycle_state"] == "paused"
        assert launches == [True]

    failed_app = create_app(
        review_runs={"archived_run": tmp_path},
        launch_profile=_dashboard_launch_profile(),
        launch_provider=lambda: (_ for _ in ()).throw(RuntimeError("port busy")),
    )
    with TestClient(failed_app) as client:
        assert client.post("/launch").json() == {
            "success": False,
            "error": "RuntimeError: port busy",
        }


def test_dashboard_launch_adopts_frozen_plan19_profile_paused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def fake_spawn(args: object, *, start_running: bool) -> dict[str, object]:
        captured["args"] = args
        captured["start_running"] = start_running
        return {
            "success": True,
            "url": "http://127.0.0.1:9021/",
            "status": {
                "lifecycle_state": "paused",
                "committed_attempts": 0,
                "target_attempts": 14,
                "provider_dispatch_count": 0,
            },
        }

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.setattr(
        "scripts.run_recoverable_evaluation._spawn", fake_spawn
    )
    result = _launch_dashboard_run(
        SimpleNamespace(
            config="config/config.yaml",
            host="127.0.0.1",
            launch_port=9021,
        )
    )
    launch_args = captured["args"]
    assert captured["start_running"] is False
    assert getattr(launch_args, "acknowledgement") == PLAN19_ACKNOWLEDGEMENT
    assert getattr(launch_args, "target_attempts") == 14
    assert getattr(launch_args, "starting_llm_budget") == 0.033192
    assert getattr(launch_args, "principal_count") == 2
    assert getattr(launch_args, "cognition_mode") == "minimal"
    assert getattr(launch_args, "policy_seed") == 24190
    assert getattr(launch_args, "port") == 9021
    assert Path(getattr(launch_args, "data_dir")).parent == tmp_path / "agent_ecology3"
    assert result["profile"] == _dashboard_launch_profile()
    assert result["status"]["provider_dispatch_count"] == 0  # type: ignore[index]


def test_spawn_uses_durable_run_cwd_and_stable_shared_client_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    data_dir = tmp_path / "durable-run"

    class FakeProcess:
        pid = 4242

        def __init__(self, _command, **kwargs):
            captured.update(kwargs)
            (data_dir / "status.json").write_text(
                json.dumps({"pid": self.pid, "lifecycle_state": "paused"}),
                encoding="utf-8",
            )

        def poll(self):
            return None

    monkeypatch.setattr(recoverable_script, "_preflight", lambda: {"success": True})
    monkeypatch.setattr(recoverable_script.subprocess, "Popen", FakeProcess)
    result = recoverable_script._spawn(
        SimpleNamespace(
            acknowledgement=PLAN19_ACKNOWLEDGEMENT,
            data_dir=str(data_dir),
            config="config/config.yaml",
            run_id="plan22_durable_worker",
            target_attempts=14,
            starting_llm_budget=0.033192,
            principal_count=2,
            cognition_mode="minimal",
            policy_seed=24190,
            host="127.0.0.1",
            port=9099,
        ),
        start_running=False,
    )
    assert captured["cwd"] == data_dir.resolve()
    assert captured["env"]["LLM_CLIENT_PROJECT"] == "agent_ecology3"  # type: ignore[index]
    assert result["pid"] == 4242


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


def test_plan19_acknowledgement_freezes_mvp_cell() -> None:
    valid = SimpleNamespace(
        acknowledgement=PLAN19_ACKNOWLEDGEMENT,
        target_attempts=14,
        starting_llm_budget=0.033192,
        principal_count=2,
        cognition_mode="minimal",
        policy_seed=24190,
    )
    _validate_start_contract(valid)

    for mutation in (
        {"target_attempts": 15},
        {"starting_llm_budget": 0.04},
        {"principal_count": 1},
        {"cognition_mode": "prescribed"},
        {"policy_seed": 24191},
    ):
        with pytest.raises(RuntimeError, match="Plan 19 requires exactly 14"):
            _validate_start_contract(SimpleNamespace(**{**vars(valid), **mutation}))


def test_plan22_acknowledgement_freezes_one_call_dashboard_canary() -> None:
    valid = SimpleNamespace(
        acknowledgement=PLAN22_CANARY_ACKNOWLEDGEMENT,
        target_attempts=1,
        starting_llm_budget=0.033192,
        principal_count=2,
        cognition_mode="minimal",
        policy_seed=24190,
    )
    _validate_start_contract(valid)

    for mutation in (
        {"target_attempts": 2},
        {"starting_llm_budget": 0.04},
        {"principal_count": 1},
        {"cognition_mode": "prescribed"},
        {"policy_seed": 24191},
    ):
        with pytest.raises(RuntimeError, match="Plan 22 canary requires exactly one"):
            _validate_start_contract(SimpleNamespace(**{**vars(valid), **mutation}))


def test_terminal_lifecycle_uses_durable_attempt_progress() -> None:
    complete_but_heartbeat_raced = {
        "lifecycle_state": "running",
        "committed_attempts": 2,
        "target_attempts": 2,
    }
    assert _terminal_lifecycle(complete_but_heartbeat_raced) == "completed"
    assert _terminal_lifecycle(
        {**complete_but_heartbeat_raced, "lifecycle_state": "invalid"}
    ) == "invalid"
    assert _terminal_lifecycle(
        {**complete_but_heartbeat_raced, "committed_attempts": 1}
    ) == "stopped"


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
