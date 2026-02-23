from __future__ import annotations

import asyncio
import json
import sys
import time
import types

import pytest

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
    assert all("decision_origin" in e for e in loop_decisions)
    assert all("forced_explore_reason" in e for e in loop_decisions)


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


def test_bootstrap_cognitive_artifacts_exist(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    world = World(cfg, run_id="test_cognitive_bootstrap")

    strategy = world.artifacts.get("alpha_1_strategy")
    state = world.artifacts.get("alpha_1_state")
    notebook = world.artifacts.get("alpha_1_notebook")
    assert strategy is not None
    assert state is not None
    assert notebook is not None
    assert "Specialization:" in strategy.content
    state_payload = json.loads(state.content)
    notebook_payload = json.loads(notebook.content)
    assert state_payload.get("next_objective") == "discover"
    assert isinstance(state_payload.get("objectives"), dict)
    assert isinstance(notebook_payload.get("journal"), list)


def test_loop_code_includes_recent_feedback_summary(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    world = World(cfg, run_id="test_loop_prompt_feedback")

    loop_artifact = world.artifacts.get("alpha_1_loop")
    assert loop_artifact is not None
    assert "_summarize_recent_feedback" in loop_artifact.code
    assert "state_snapshot[\"recent_feedback\"] = _summarize_recent_feedback(limit=40)" in loop_artifact.code
    assert "feedback = kernel_state.get_recent_feedback(limit=limit)" in loop_artifact.code
    assert "return bool(kernel_state.llm_cooldown_ready())" in loop_artifact.code
    assert "allowed_actions = {" in loop_artifact.code
    assert "\"transfer_resource\"" in loop_artifact.code
    assert "disallowed_action:" in loop_artifact.code
    assert "avoid repeating actions with recent error codes" in loop_artifact.code
    assert "_build_memory_snapshot" in loop_artifact.code
    assert "memory.next_objective" in loop_artifact.code
    assert "readable_only=True" in loop_artifact.code
    assert "include_permissions=True" in loop_artifact.code
    assert "params.setdefault(\"readable_only\", True)" in loop_artifact.code
    assert "if \"read_price\" not in normalized and not artifact_id.endswith(\"_scratch\")" in loop_artifact.code
    assert "if priced_non_scratch is not None:" in loop_artifact.code
    assert "if priced_scratch is not None:" in loop_artifact.code


def test_loop_code_uses_custom_prompt_template_path(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    prompt_template = tmp_path / "loop_prompt.txt"
    prompt_template.write_text(
        "Custom prompt for {principal_id}. Choose one action and never use noop.",
        encoding="utf-8",
    )
    cfg.llm.loop_prompt_template_path = str(prompt_template)
    world = World(cfg, run_id="test_loop_custom_prompt_template")

    loop_artifact = world.artifacts.get("alpha_1_loop")
    assert loop_artifact is not None
    assert "Custom prompt for alpha_1. Choose one action and never use noop." in loop_artifact.code
    assert "You are agent alpha_1 in an economy simulation." not in loop_artifact.code


def test_query_artifacts_readable_only_filters_unreadable(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    cfg.principals.count = 2
    world = World(cfg, run_id="test_query_artifacts_readable_only")

    shared = world.execute_action_data(
        "alpha_2",
        {
            "action_type": "write_artifact",
            "artifact_id": "alpha_2_shared_note",
            "artifact_type": "note",
            "content": "shared",
            "executable": False,
        },
    )
    assert shared.success, shared.message

    query = world.execute_action_data(
        "alpha_1",
        {
            "action_type": "query_kernel",
            "query_type": "artifacts",
            "params": {"readable_only": True, "include_permissions": True, "limit": 200},
        },
    )
    assert query.success, query.message
    assert isinstance(query.data, dict)
    rows = query.data.get("results", [])
    assert isinstance(rows, list)
    assert rows

    row_ids = [row.get("id") for row in rows if isinstance(row, dict)]
    assert "alpha_2_shared_note" in row_ids
    assert "alpha_2_strategy" not in row_ids
    assert "alpha_2_state" not in row_ids
    assert "alpha_2_notebook" not in row_ids

    for row in rows:
        assert isinstance(row, dict)
        assert row.get("readable") is True


def test_loop_updates_cognitive_state_and_notebook(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    world = World(cfg, run_id="test_loop_memory_update")

    state_before = json.loads(world.artifacts.get("alpha_1_state").content)  # type: ignore[union-attr]
    notebook_before = json.loads(world.artifacts.get("alpha_1_notebook").content)  # type: ignore[union-attr]

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

    state_after = json.loads(world.artifacts.get("alpha_1_state").content)  # type: ignore[union-attr]
    notebook_after = json.loads(world.artifacts.get("alpha_1_notebook").content)  # type: ignore[union-attr]
    assert int(state_after.get("iteration", 0)) >= int(state_before.get("iteration", 0)) + 1
    assert isinstance(state_after.get("recent_actions"), list)
    assert state_after["recent_actions"], "recent_actions should record loop decisions"
    assert isinstance(notebook_after.get("journal"), list)
    assert len(notebook_after["journal"]) >= len(notebook_before.get("journal", []))



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
        world.mark_llm_call_attempt("alpha_1")
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


def test_loop_llm_cooldown_ignores_log_volume(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    cfg.llm.enable_bootstrap_loop_llm = True
    cfg.llm.loop_action_gate_enabled = True
    cfg.llm.loop_llm_cooldown_seconds = 60.0
    world = World(cfg, run_id="test_loop_llm_cooldown_log_volume")

    llm_call_count = {"n": 0}

    def _fake_syscall(**_kwargs):
        llm_call_count["n"] += 1
        world.mark_llm_call_attempt("alpha_1")
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

    for i in range(400):
        world.logger.log("noise_event", {"event_number": world.event_number, "noise_index": i})

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

    loop_decisions = [e for e in world.logger.read_recent(120) if e.get("event_type") == "loop_decision"]
    assert loop_decisions
    assert loop_decisions[-1].get("decision_source") == "llm_cooldown_skip"


def _stub_llm_result(
    *,
    content: str = "{}",
    tool_calls: list[dict[str, object]] | None = None,
) -> object:
    class _Result:
        pass

    result = _Result()
    result.content = content
    result.tool_calls = tool_calls or []
    result.usage = {"prompt_tokens": 6, "completion_tokens": 4, "total_tokens": 10}
    result.cost = 0.0
    result.marginal_cost = 0.0
    result.cost_source = "subscription_included"
    result.billing_mode = "subscription_included"
    result.cache_hit = False
    return result


def test_subscription_included_charges_estimated_budget_by_default(tmp_path, monkeypatch) -> None:
    cfg = _make_config(tmp_path)
    cfg.llm.subscription_budget_charge_mode = "estimated"
    cfg.llm.subscription_estimated_cost_multiplier = 1.0
    world = World(cfg, run_id="test_subscription_budget_estimated")

    def _fake_call_llm(**_kwargs):
        return _stub_llm_result(content='{"action_type":"query_kernel","query_type":"resources","params":{}}')

    fake_module = types.ModuleType("llm_client")
    fake_module.call_llm = _fake_call_llm
    monkeypatch.setitem(sys.modules, "llm_client", fake_module)

    before_budget = world.ledger.get_llm_budget("alpha_1")
    result = world.call_llm_as_syscall(
        payer_id="alpha_1",
        model="claude-code/opus",
        messages=[{"role": "user", "content": "short test prompt"}],
    )
    after_budget = world.ledger.get_llm_budget("alpha_1")

    assert result.get("success") is True
    assert result.get("budget_charge_basis") == "subscription_estimated"
    assert float(result.get("charged_cost", 0.0)) > 0.0
    assert after_budget < before_budget

    llm_events = [e for e in world.logger.read_recent(20) if e.get("event_type") == "llm_syscall"]
    assert llm_events
    assert llm_events[-1].get("budget_charge_basis") == "subscription_estimated"


def test_subscription_included_budget_mode_none_refunds_budget(tmp_path, monkeypatch) -> None:
    cfg = _make_config(tmp_path)
    cfg.llm.subscription_budget_charge_mode = "none"
    world = World(cfg, run_id="test_subscription_budget_none")

    def _fake_call_llm(**_kwargs):
        return _stub_llm_result(content='{"action_type":"query_kernel","query_type":"resources","params":{}}')

    fake_module = types.ModuleType("llm_client")
    fake_module.call_llm = _fake_call_llm
    monkeypatch.setitem(sys.modules, "llm_client", fake_module)

    before_budget = world.ledger.get_llm_budget("alpha_1")
    result = world.call_llm_as_syscall(
        payer_id="alpha_1",
        model="claude-code/opus",
        messages=[{"role": "user", "content": "short test prompt"}],
    )
    after_budget = world.ledger.get_llm_budget("alpha_1")

    assert result.get("success") is True
    assert result.get("budget_charge_basis") == "subscription_none"
    assert float(result.get("charged_cost", -1.0)) == pytest.approx(0.0)
    assert after_budget == pytest.approx(before_budget)


def test_syscall_injects_claude_mcp_server_for_ae3_action_tool(tmp_path, monkeypatch) -> None:
    cfg = _make_config(tmp_path)
    world = World(cfg, run_id="test_claude_mcp_bridge")

    captured: dict[str, object] = {}

    def _fake_call_llm(**kwargs):
        captured.update(kwargs)
        return _stub_llm_result(content='{"action_type":"write_artifact","artifact_id":"alpha_1_scratch"}')

    fake_module = types.ModuleType("llm_client")
    fake_module.call_llm = _fake_call_llm
    monkeypatch.setitem(sys.modules, "llm_client", fake_module)

    result = world.call_llm_as_syscall(
        payer_id="alpha_1",
        model="claude-code/opus",
        messages=[{"role": "user", "content": "test"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "ae3_action",
                    "parameters": {
                        "type": "object",
                        "properties": {"action_type": {"type": "string"}},
                    },
                },
            }
        ],
    )
    assert result.get("success") is True
    mcp_servers = captured.get("mcp_servers")
    assert isinstance(mcp_servers, dict)
    bridge = mcp_servers.get("ae3-loop-action")
    assert isinstance(bridge, dict)
    assert bridge.get("type") == "stdio"
    assert bridge.get("command")
    args = bridge.get("args")
    assert isinstance(args, list)
    assert args
    assert str(args[0]).endswith("loop_action_server.py")


def test_syscall_does_not_inject_mcp_server_for_non_claude_model(tmp_path, monkeypatch) -> None:
    cfg = _make_config(tmp_path)
    world = World(cfg, run_id="test_non_claude_no_mcp_bridge")

    captured: dict[str, object] = {}

    def _fake_call_llm(**kwargs):
        captured.update(kwargs)
        return _stub_llm_result(content='{"action_type":"write_artifact","artifact_id":"alpha_1_scratch"}')

    fake_module = types.ModuleType("llm_client")
    fake_module.call_llm = _fake_call_llm
    monkeypatch.setitem(sys.modules, "llm_client", fake_module)

    result = world.call_llm_as_syscall(
        payer_id="alpha_1",
        model="openrouter/deepseek/deepseek-chat",
        messages=[{"role": "user", "content": "test"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "ae3_action",
                    "parameters": {
                        "type": "object",
                        "properties": {"action_type": {"type": "string"}},
                    },
                },
            }
        ],
    )
    assert result.get("success") is True
    assert "mcp_servers" not in captured


def test_transfer_resource_moves_llm_budget(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    cfg.principals.count = 2
    world = World(cfg, run_id="test_transfer_resource")

    before_sender = world.ledger.get_llm_budget("alpha_1")
    before_recipient = world.ledger.get_llm_budget("alpha_2")

    result = world.execute_action_data(
        "alpha_1",
        {
            "action_type": "transfer_resource",
            "recipient_id": "alpha_2",
            "resource": "llm_budget",
            "amount": 0.5,
            "memo": "contracted budget",
        },
    )
    assert result.success, result.message

    assert world.ledger.get_llm_budget("alpha_1") == pytest.approx(before_sender - 0.5)
    assert world.ledger.get_llm_budget("alpha_2") == pytest.approx(before_recipient + 0.5)

    events = [e for e in world.logger.read_recent(40) if e.get("event_type") == "resource_transfer"]
    assert events
    last = events[-1]
    assert last.get("resource") == "llm_budget"
    assert last.get("sender") == "alpha_1"
    assert last.get("recipient") == "alpha_2"


def test_transfer_resource_rejects_non_transferable_resource(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    cfg.principals.count = 2
    world = World(cfg, run_id="test_transfer_resource_invalid")

    result = world.execute_action_data(
        "alpha_1",
        {
            "action_type": "transfer_resource",
            "recipient_id": "alpha_2",
            "resource": "llm_calls",
            "amount": 1,
        },
    )
    assert result.success is False
    assert result.error_code == "invalid_argument"
