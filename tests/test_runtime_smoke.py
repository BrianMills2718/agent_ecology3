from __future__ import annotations

import asyncio
import json
import time

from agent_ecology3.config import AppConfig
from agent_ecology3.simulation import SimulationRunner
from agent_ecology3.world import World


def _make_config(tmp_path) -> AppConfig:
    cfg = AppConfig()
    cfg.principals.count = 1
    cfg.principals.id_prefix = "alpha_"
    cfg.principals.starting_scrip = 100
    cfg.principals.starting_llm_budget = 1.0
    cfg.principals.starting_disk_quota_bytes = 100_000

    cfg.simulation.default_duration_seconds = 0.8
    cfg.simulation.max_runtime_seconds = 10
    cfg.simulation.loop.min_delay_seconds = 0.05
    cfg.simulation.loop.max_delay_seconds = 0.25
    cfg.simulation.loop.max_consecutive_errors = 3
    cfg.simulation.loop.resource_check_interval_seconds = 0.05
    cfg.simulation.summary_interval_seconds = 0.5

    cfg.llm.enable_bootstrap_loop_llm = False
    cfg.dashboard.enabled = False

    cfg.logging.logs_dir = str(tmp_path / "logs")
    cfg.logging.recent_event_limit = 1000
    return cfg


def test_world_write_read_roundtrip(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    world = World(cfg, run_id="test_roundtrip")

    write_result = world.execute_action_data(
        "alpha_1",
        {
            "action_type": "write_artifact",
            "artifact_id": "alpha_1_note",
            "artifact_type": "note",
            "content": "hello world",
            "executable": False,
        },
    )
    assert write_result.success, write_result.message

    read_result = world.execute_action_data(
        "alpha_1",
        {
            "action_type": "read_artifact",
            "artifact_id": "alpha_1_note",
        },
    )
    assert read_result.success, read_result.message
    assert read_result.data is not None
    artifact = read_result.data.get("artifact", {})
    assert artifact.get("content") == "hello world"


def test_runner_executes_bootstrap_loop(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    world = World(cfg, run_id="test_runner")
    runner = SimulationRunner(world)

    asyncio.run(runner.run(duration=1.0))

    assert world.event_number > 0
    events = world.logger.read_recent(500)
    event_types = {e.get("event_type") for e in events}
    assert "simulation_started" in event_types
    assert "simulation_stopped" in event_types
    assert "invoke_success" in event_types or "invoke_failure" in event_types
    loop_decisions = [e for e in events if e.get("event_type") == "loop_decision"]
    assert loop_decisions, "expected loop_decision trace events"
    assert any(isinstance(e.get("decision_action"), str) and e.get("decision_action") for e in loop_decisions)
    assert all("fallback_used" in e for e in loop_decisions)
    assert all("decision_source" in e for e in loop_decisions)


def test_loop_artifact_is_kernel_protected(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    world = World(cfg, run_id="test_loop_protection")

    loop_artifact = world.artifacts.get("alpha_1_loop")
    assert loop_artifact is not None
    assert loop_artifact.kernel_protected is True

    overwrite = world.execute_action_data(
        "alpha_1",
        {
            "action_type": "write_artifact",
            "artifact_id": "alpha_1_loop",
            "artifact_type": "agent_loop",
            "content": "overwrite attempt",
            "executable": False,
        },
    )
    assert overwrite.success is False
    assert overwrite.error_code == "not_authorized"


def test_loop_code_includes_recent_feedback_summary(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    world = World(cfg, run_id="test_loop_prompt_feedback")

    loop_artifact = world.artifacts.get("alpha_1_loop")
    assert loop_artifact is not None
    assert "_summarize_recent_feedback" in loop_artifact.code
    assert "state_snapshot[\"recent_feedback\"] = _summarize_recent_feedback(limit=40)" in loop_artifact.code
    assert "if intent_principal != \"alpha_1\":" in loop_artifact.code
    assert "allowed_actions = {" in loop_artifact.code
    assert "disallowed_action:" in loop_artifact.code
    assert "avoid repeating actions with recent error codes" in loop_artifact.code


def test_loop_action_gate_rewrites_disallowed_llm_action(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    cfg.llm.enable_bootstrap_loop_llm = True
    cfg.llm.loop_action_gate_enabled = True
    cfg.llm.loop_llm_cooldown_seconds = 0.0
    world = World(cfg, run_id="test_loop_action_gate")

    world.call_llm_as_syscall = lambda **_: {
        "success": True,
        "content": json.dumps(
            {
                "action_type": "mint",
                "recipient_id": "alpha_2",
                "amount": 1,
                "reason": "disallowed for loop",
            }
        ),
        "usage": {"total_tokens": 10},
        "cost": 0.0,
        "charged_cost": 0.0,
        "cost_source": "test",
        "billing_mode": "subscription",
        "cache_hit": False,
        "undercharged_cost": 0.0,
    }

    gate_triggered = False
    for _ in range(30):
        invoke_result = world.execute_action_data(
            "alpha_1",
            {
                "action_type": "invoke_artifact",
                "artifact_id": "alpha_1_loop",
                "method": "run",
                "args": [],
            },
        )
        assert invoke_result.success, invoke_result.message

        events = world.logger.read_recent(50)
        loop_decision_events = [e for e in events if e.get("event_type") == "loop_decision"]
        assert loop_decision_events
        last = loop_decision_events[-1]
        if bool(last.get("forced_explore")):
            time.sleep(0.05)
            continue
        if bool(last.get("gate_fallback_used")):
            gate_triggered = True
            assert str(last.get("gate_reason", "")).startswith("disallowed_action:mint")
            assert last.get("raw_decision_action") == "mint"
            assert last.get("decision_action") != "mint"
            break

    assert gate_triggered, "expected action gate to trigger on disallowed LLM action"


def test_loop_llm_cooldown_skips_rapid_repeated_calls(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    cfg.llm.enable_bootstrap_loop_llm = True
    cfg.llm.loop_action_gate_enabled = True
    cfg.llm.loop_llm_cooldown_seconds = 60.0
    world = World(cfg, run_id="test_loop_llm_cooldown")

    llm_call_count = {"n": 0}

    def _fake_syscall(**_kwargs):
        llm_call_count["n"] += 1
        world.logger.log(
            "llm_syscall",
            {
                "event_number": world.event_number,
                "payer_id": "alpha_1",
                "model": "test-model",
                "duration_ms": 1.0,
                "charged_cost": 0.0,
            },
        )
        return {
            "success": True,
            "content": json.dumps(
                {
                    "action_type": "read_artifact",
                    "artifact_id": "alpha_1_scratch",
                }
            ),
            "usage": {"total_tokens": 10},
            "cost": 0.0,
            "charged_cost": 0.0,
            "cost_source": "test",
            "billing_mode": "subscription",
            "cache_hit": False,
            "undercharged_cost": 0.0,
        }

    world.call_llm_as_syscall = _fake_syscall

    for _ in range(2):
        invoke_result = world.execute_action_data(
            "alpha_1",
            {
                "action_type": "invoke_artifact",
                "artifact_id": "alpha_1_loop",
                "method": "run",
                "args": [],
            },
        )
        assert invoke_result.success, invoke_result.message

    assert llm_call_count["n"] == 1
    loop_decisions = [e for e in world.logger.read_recent(50) if e.get("event_type") == "loop_decision"]
    assert len(loop_decisions) >= 2
    last = loop_decisions[-1]
    assert last.get("decision_source") == "llm_cooldown_skip"
    assert last.get("llm_attempted") is False
