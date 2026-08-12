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

model_override_acceptance = {
    "accepted_by": "brian",
    "reason": "Runtime smoke tests exercise Claude bridge and non-Claude branches; MiniMax-M3 remains the default model.",
}


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


def test_runner_monitor_remains_responsive_during_slow_async_syscall(tmp_path) -> None:
    async def _exercise() -> None:
        cfg = _make_config(tmp_path)
        cfg.llm.enable_bootstrap_loop_llm = True
        world = World(cfg, run_id="test_async_monitor")
        runner = SimulationRunner(world)
        started = asyncio.Event()
        release = asyncio.Event()
        heartbeat_count = 0

        async def _slow_syscall(**_kwargs):
            started.set()
            await release.wait()
            return {
                "success": True,
                "trace_id": "ae3/test_async_monitor/event_1/payer/alpha_1",
                "content": "",
                "tool_calls": [
                    {
                        "id": "monitor-call",
                        "type": "function",
                        "function": {
                            "name": "ae3_action",
                            "arguments": '{"action_type":"query_kernel","query_type":"resources"}',
                        },
                    }
                ],
            }

        def _blocking_old_syscall(**_kwargs):
            time.sleep(0.15)
            return {
                "success": True,
                "trace_id": "ae3/test_async_monitor/old-boundary",
                "content": '{"action_type":"query_kernel","query_type":"resources"}',
                "tool_calls": [],
            }

        async def _heartbeat() -> None:
            nonlocal heartbeat_count
            while not runner._stop_requested:
                heartbeat_count += 1
                await asyncio.sleep(0.01)

        world.call_llm_as_syscall = _blocking_old_syscall  # type: ignore[method-assign]
        world.call_llm_as_syscall_async = _slow_syscall  # type: ignore[method-assign]
        run_task = asyncio.create_task(runner.run(duration=0.05))
        heartbeat_task = asyncio.create_task(_heartbeat())
        await asyncio.wait_for(started.wait(), timeout=0.5)
        await asyncio.sleep(0.12)

        assert heartbeat_count >= 5
        assert runner._stop_requested is True
        assert run_task.done() is False

        release.set()
        await asyncio.wait_for(run_task, timeout=0.5)
        await heartbeat_task

    asyncio.run(_exercise())


def test_runner_drains_inflight_loop_before_returning(tmp_path) -> None:
    async def _exercise() -> None:
        cfg = _make_config(tmp_path)
        cfg.llm.enable_bootstrap_loop_llm = True
        world = World(cfg, run_id="test_async_drain")
        runner = SimulationRunner(world)
        started = asyncio.Event()
        release = asyncio.Event()
        completed = False

        async def _slow_syscall(**_kwargs):
            nonlocal completed
            started.set()
            await release.wait()
            completed = True
            return {
                "success": True,
                "trace_id": "ae3/test_async_drain/event_1/payer/alpha_1",
                "content": '{"action_type":"query_kernel","query_type":"resources"}',
                "tool_calls": [],
            }

        def _blocking_old_syscall(**_kwargs):
            time.sleep(0.15)
            return {
                "success": True,
                "trace_id": "ae3/test_async_drain/old-boundary",
                "content": '{"action_type":"query_kernel","query_type":"resources"}',
                "tool_calls": [],
            }

        world.call_llm_as_syscall = _blocking_old_syscall  # type: ignore[method-assign]
        world.call_llm_as_syscall_async = _slow_syscall  # type: ignore[method-assign]
        run_task = asyncio.create_task(runner.run(duration=0.05))
        await asyncio.wait_for(started.wait(), timeout=0.5)
        await asyncio.sleep(0.12)

        assert runner._stop_requested is True
        assert run_task.done() is False
        assert completed is False

        release.set()
        await asyncio.wait_for(run_task, timeout=0.5)
        returned_event_number = world.event_number
        assert completed is True
        await asyncio.sleep(0.05)
        assert world.event_number == returned_event_number

    asyncio.run(_exercise())


def test_runner_serializes_loop_world_mutations(tmp_path) -> None:
    async def _exercise() -> None:
        cfg = _make_config(tmp_path)
        cfg.principals.count = 2
        cfg.llm.enable_bootstrap_loop_llm = True
        world = World(cfg, run_id="test_async_serial")
        runner = SimulationRunner(world)
        active = 0
        maximum_active = 0

        async def _slow_syscall(**kwargs):
            nonlocal active, maximum_active
            active += 1
            maximum_active = max(maximum_active, active)
            await asyncio.sleep(0.03)
            active -= 1
            payer = str(kwargs["payer_id"])
            return {
                "success": True,
                "trace_id": f"ae3/test_async_serial/event_1/payer/{payer}",
                "content": '{"action_type":"query_kernel","query_type":"resources"}',
                "tool_calls": [],
            }

        def _blocking_old_syscall(**kwargs):
            time.sleep(0.03)
            payer = str(kwargs["payer_id"])
            return {
                "success": True,
                "trace_id": f"ae3/test_async_serial/old-boundary/{payer}",
                "content": '{"action_type":"query_kernel","query_type":"resources"}',
                "tool_calls": [],
            }

        world.call_llm_as_syscall = _blocking_old_syscall  # type: ignore[method-assign]
        world.call_llm_as_syscall_async = _slow_syscall  # type: ignore[method-assign]
        await asyncio.wait_for(runner.run(duration=0.16), timeout=0.8)

        assert maximum_active == 1

    asyncio.run(_exercise())


def test_legacy_sync_artifact_can_still_invoke_nested_artifact(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    world = World(cfg, run_id="test_sync_nested_compatibility")
    for artifact_id, code in (
        ("alpha_1_target", "def run():\n    return {'value': 7}\n"),
        ("alpha_1_wrapper", "def run():\n    return invoke('alpha_1_target')\n"),
    ):
        write = world.execute_action_data(
            "alpha_1",
            {
                "action_type": "write_artifact",
                "artifact_id": artifact_id,
                "artifact_type": "tool",
                "content": "sync compatibility fixture",
                "executable": True,
                "code": code,
            },
        )
        assert write.success, write.message

    invoked = world.execute_action_data(
        "alpha_1",
        {
            "action_type": "invoke_artifact",
            "artifact_id": "alpha_1_wrapper",
            "method": "run",
            "args": [],
        },
    )

    assert invoked.success, invoked.message
    assert invoked.data is not None
    nested = invoked.data["result"]
    assert nested["success"] is True
    assert nested["data"]["result"]["value"] == 7


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


def test_minimal_cognition_omits_prescribed_roles_and_objectives(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    cfg.llm.loop_cognition_mode = "minimal"
    world = World(cfg, run_id="test_minimal_cognition")

    strategy = world.artifacts.get("alpha_1_strategy")
    state = world.artifacts.get("alpha_1_state")
    notebook = world.artifacts.get("alpha_1_notebook")
    loop = world.artifacts.get("alpha_1_loop")
    assert strategy is not None
    assert state is not None
    assert notebook is not None
    assert loop is not None
    assert "Specialization:" not in strategy.content
    assert "Cycle goals:" not in strategy.content
    state_payload = json.loads(state.content)
    notebook_payload = json.loads(notebook.content)
    assert "role" not in state_payload
    assert "specialization" not in state_payload
    assert "objectives" not in state_payload
    assert "next_objective" not in state_payload
    assert "role" not in notebook_payload["key_facts"]
    assert "if True:" in loop.code
    assert "False\n            and \"read_price\" not in normalized" in loop.code


def test_minimal_invalid_output_falls_back_only_to_self_resource_query(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    cfg.llm.loop_cognition_mode = "minimal"
    cfg.llm.enable_bootstrap_loop_llm = True
    world = World(cfg, run_id="test_minimal_fallback")
    world.call_llm_as_syscall = lambda **_: {
        "success": True,
        "trace_id": "ae3/test_minimal_fallback/event_1/payer/alpha_1",
        "content": '{"action_type":"mint"}',
        "tool_calls": [],
    }

    result = world.execute_action_data(
        "alpha_1",
        {
            "action_type": "invoke_artifact",
            "artifact_id": "alpha_1_loop",
            "method": "run",
            "args": [],
        },
    )
    assert result.success, result.message
    decisions = [e for e in world.logger.read_recent(50) if e.get("event_type") == "loop_decision"]
    assert decisions
    assert decisions[-1]["decision_action"] == "query_kernel"
    assert decisions[-1]["gate_fallback_used"] is True
    assert decisions[-1]["llm_trace_id"] == "ae3/test_minimal_fallback/event_1/payer/alpha_1"


def test_minimal_valid_write_is_not_auto_priced(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    cfg.llm.loop_cognition_mode = "minimal"
    cfg.llm.enable_bootstrap_loop_llm = True
    world = World(cfg, run_id="test_minimal_no_auto_price")
    world.call_llm_as_syscall = lambda **_: {
        "success": True,
        "trace_id": "ae3/test_minimal_no_auto_price/event_1/payer/alpha_1",
        "content": json.dumps(
            {
                "action_type": "write_artifact",
                "artifact_id": "alpha_1_offer",
                "artifact_type": "note",
                "content": "self-selected output",
            }
        ),
        "tool_calls": [],
    }

    result = world.execute_action_data(
        "alpha_1",
        {
            "action_type": "invoke_artifact",
            "artifact_id": "alpha_1_loop",
            "method": "run",
            "args": [],
        },
    )
    assert result.success, result.message
    artifact = world.artifacts.get("alpha_1_offer")
    assert artifact is not None
    assert artifact.read_price == 0


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
    assert "True\n            and \"read_price\" not in normalized" in loop_artifact.code
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


def test_syscall_logs_and_returns_trace_id_and_budget_controls(tmp_path, monkeypatch) -> None:
    cfg = _make_config(tmp_path)
    cfg.llm.num_retries = 0
    cfg.llm.max_output_tokens = 512
    cfg.llm.provider_max_budget_usd = 0.25
    cfg.llm.provider_budget_reservation_usd = 0.01
    world = World(cfg, run_id="test_trace_budget")
    captured: dict[str, object] = {}

    def _fake_call_llm(**kwargs):
        captured.update(kwargs)
        return _stub_llm_result(content='{"action_type":"query_kernel","query_type":"resources","params":{}}')

    fake_module = types.ModuleType("llm_client")
    fake_module.call_llm = _fake_call_llm
    monkeypatch.setitem(sys.modules, "llm_client", fake_module)

    result = world.call_llm_as_syscall(
        payer_id="alpha_1",
        model="minimax/minimax-m3",
        messages=[{"role": "user", "content": "test"}],
    )

    expected_trace = "ae3/test_trace_budget/event_0/payer/alpha_1"
    assert result["trace_id"] == expected_trace
    assert captured["trace_id"] == expected_trace
    assert captured["model_justification"] == cfg.llm.model_justification
    assert captured["num_retries"] == 0
    assert captured["max_tokens"] == 512
    assert captured["max_budget"] == pytest.approx(0.25)
    assert captured["budget_scope_trace_id"] == "ae3/test_trace_budget"
    assert captured["budget_reservation"] == pytest.approx(0.01)
    events = [e for e in world.logger.read_recent(20) if e.get("event_type") == "llm_syscall"]
    assert events[-1]["trace_id"] == expected_trace


def test_async_syscall_uses_shared_accounting_and_native_async_client(tmp_path, monkeypatch) -> None:
    cfg = _make_config(tmp_path)
    cfg.llm.num_retries = 0
    cfg.llm.max_output_tokens = 512
    cfg.llm.provider_max_budget_usd = 0.25
    cfg.llm.provider_budget_reservation_usd = 0.01
    world = World(cfg, run_id="test_async_trace_budget")
    captured: dict[str, object] = {}

    async def _fake_acall_llm(**kwargs):
        captured.update(kwargs)
        await asyncio.sleep(0)
        return _stub_llm_result(
            content="",
            tool_calls=[
                {
                    "id": "async-call",
                    "type": "function",
                    "function": {
                        "name": "ae3_action",
                        "arguments": '{"action_type":"query_kernel","query_type":"resources"}',
                    },
                }
            ],
        )

    def _unexpected_sync_call(**_kwargs):
        raise AssertionError("async syscall dispatched through call_llm")

    fake_module = types.ModuleType("llm_client")
    fake_module.acall_llm = _fake_acall_llm
    fake_module.call_llm = _unexpected_sync_call
    monkeypatch.setitem(sys.modules, "llm_client", fake_module)

    result = asyncio.run(
        world.call_llm_as_syscall_async(
            payer_id="alpha_1",
            model="minimax/minimax-m3",
            messages=[{"role": "user", "content": "short test prompt"}],
            tools=World.build_loop_action_tools(),
        )
    )

    expected_trace = "ae3/test_async_trace_budget/event_0/payer/alpha_1"
    assert result.get("success") is True
    assert result.get("trace_id") == expected_trace
    assert len(result.get("tool_calls", [])) == 1
    assert captured.get("num_retries") == 0
    assert captured.get("max_tokens") == 512
    assert captured.get("max_budget") == pytest.approx(0.25)
    assert captured.get("budget_reservation") == pytest.approx(0.01)
    events = [e for e in world.logger.read_recent(20) if e.get("event_type") == "llm_syscall"]
    assert len(events) == 1
    assert events[0].get("trace_id") == expected_trace


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
    assert captured.get("max_retries") == 0
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
        model="minimax/minimax-m3",
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
    assert "max_retries" not in captured


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


def test_runner_stops_after_exact_settled_attempt_target(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    cfg.principals.count = 4
    cfg.llm.enable_bootstrap_loop_llm = True
    cfg.llm.loop_forced_explore_mode = "off"
    cfg.simulation.loop.min_delay_seconds = 0.001
    cfg.simulation.loop.max_delay_seconds = 0.002
    world = World(cfg, run_id="test_exact_attempt_stop")
    runner = SimulationRunner(world)
    attempts = 0

    async def _fake_call_llm_as_syscall_async(**kwargs):
        nonlocal attempts
        attempts += 1
        trace_id = f"ae3/test_exact_attempt_stop/attempt_{attempts}"
        tool_call = {
            "id": f"call-{attempts}",
            "type": "function",
            "function": {
                "name": "ae3_action",
                "arguments": (
                    '{"action_type":"query_kernel","query_type":"resources",'
                    '"params":{}}'
                ),
            },
        }
        world.logger.log(
            "llm_syscall",
            {
                "event_number": world.event_number,
                "trace_id": trace_id,
                "payer_id": kwargs["payer_id"],
                "model": kwargs["model"],
                "actual_cost": 0.0,
                "charged_cost": 0.0,
                "cache_hit": False,
                "tool_calls_count": 1,
            },
        )
        return {
            "success": True,
            "trace_id": trace_id,
            "content": "",
            "tool_calls": [tool_call],
            "cost": 0.0,
            "charged_cost": 0.0,
            "cache_hit": False,
        }

    world.call_llm_as_syscall_async = _fake_call_llm_as_syscall_async  # type: ignore[method-assign]
    asyncio.run(runner.run(duration=3.0, target_llm_attempts=16))

    events = world.logger.read_recent(1000)
    attempt_events = [
        event
        for event in events
        if event.get("event_type") in {"llm_syscall", "llm_syscall_error"}
    ]
    decisions = [event for event in events if event.get("event_type") == "loop_decision"]
    assert attempts == 16
    assert len(attempt_events) == 16
    assert len(decisions) == 16
    assert decisions[-1]["llm_trace_id"] == "ae3/test_exact_attempt_stop/attempt_16"
