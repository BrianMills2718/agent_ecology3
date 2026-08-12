"""Provider-free tests for Plan 10's Luna structured-action slice."""

from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from typing import Any

import llm_client
import pytest
from pydantic import ValidationError

from agent_ecology3.analysis.luna_recovery_gate import (
    REVIEWED_LLM_CLIENT_REVISION,
    build_provider_free_preflight,
)
from agent_ecology3.config import AppConfig, LLMConfig, load_config
from agent_ecology3.world.actions import ActionIntent
from agent_ecology3.world.luna_actions import (
    LUNA_ACTION_TYPES,
    LUNA_MODEL,
    LunaLoopDecisionV1,
    luna_provider_schema,
    validate_luna_action_for_principal,
)
from agent_ecology3.world.world import World

LLM_CLIENT_REPO = Path(llm_client.__file__).resolve().parents[1]


def _luna_profile() -> dict[str, Any]:
    return {
        "default_model": LUNA_MODEL,
        "allowed_models": [LUNA_MODEL],
        "num_retries": 0,
        "agent_cwd": None,
        "decision_output_mode": "luna_structured_v1",
        "reasoning_effort": "medium",
        "codex_transport": "cli",
        "codex_sandbox_mode": "read-only",
        "codex_approval_policy": "never",
        "codex_isolate_home": True,
        "structured_response_model": "LunaLoopDecisionV1",
        "expected_billing_mode": "subscription_included",
    }


def _configured_world(tmp_path: Path, *, bootstrap_loop_llm: bool = False) -> World:
    cfg = AppConfig(llm=LLMConfig(**_luna_profile()))
    cfg.principals.count = 1
    cfg.principals.starting_llm_budget = 1.0
    cfg.llm.enable_bootstrap_loop_llm = bootstrap_loop_llm
    cfg.logging.logs_dir = str(tmp_path / "logs")
    cfg.dashboard.enabled = False
    return World(cfg, run_id="test_luna_structured")


def _llm_result(content: str) -> object:
    class Result:
        pass

    result = Result()
    result.content = content
    result.usage = {"input_tokens": 8, "output_tokens": 4, "total_tokens": 12}
    result.cost = 0.0
    result.marginal_cost = 0.0
    result.cost_source = "subscription_included"
    result.billing_mode = "subscription_included"
    result.cache_hit = False
    result.requested_model = LUNA_MODEL
    result.resolved_model = LUNA_MODEL
    result.model = LUNA_MODEL
    result.raw_response = {"transport": "codex_cli"}
    result.tool_calls = []
    result.codex_events = []
    return result


def test_luna_route_requires_exact_medium_cli_profile() -> None:
    accepted = LLMConfig(**_luna_profile())
    assert accepted.reasoning_effort == "medium"

    for field, invalid in (
        ("default_model", "codex/gpt-5.6-terra"),
        ("reasoning_effort", "low"),
        ("codex_transport", "auto"),
        ("codex_sandbox_mode", "workspace-write"),
        ("codex_approval_policy", "on-request"),
        ("codex_isolate_home", False),
        ("structured_response_model", None),
        ("expected_billing_mode", "api_metered"),
        ("num_retries", 1),
        ("agent_cwd", "."),
    ):
        profile = _luna_profile()
        profile[field] = invalid
        with pytest.raises(ValidationError, match="exact Plan 10 profile"):
            LLMConfig(**profile)


def test_luna_action_schema_projects_six_permitted_variants() -> None:
    schema = luna_provider_schema()
    action_schema = schema["properties"]["action"]
    assert len(action_schema["anyOf"]) == 6
    assert "oneOf" not in action_schema

    def assert_closed(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
            for value in node.values():
                assert_closed(value)
        elif isinstance(node, list):
            for value in node:
                assert_closed(value)

    assert_closed(schema)

    payloads = (
        {
            "schema_version": "luna_loop_decision.v1",
            "action": {
                "action_type": "write_artifact",
                "artifact_id": "alpha_1_note",
                "artifact_type": "note",
                "content": "hello",
            },
        },
        {
            "schema_version": "luna_loop_decision.v1",
            "action": {"action_type": "read_artifact", "artifact_id": "alpha_2_note"},
        },
        {
            "schema_version": "luna_loop_decision.v1",
            "action": {"action_type": "transfer", "recipient_id": "alpha_2", "amount": 1},
        },
        {
            "schema_version": "luna_loop_decision.v1",
            "action": {
                "action_type": "transfer_resource",
                "recipient_id": "alpha_2",
                "resource": "llm_budget",
                "amount": 0.1,
            },
        },
        {
            "schema_version": "luna_loop_decision.v1",
            "action": {"action_type": "submit_to_mint", "artifact_id": "alpha_1_note", "bid": 1},
        },
        {
            "schema_version": "luna_loop_decision.v1",
            "action": {
                "action_type": "query_kernel",
                "query_type": "artifacts",
                "params": {"limit": 10, "readable_only": True},
            },
        },
    )
    observed: set[str] = set()
    for payload in payloads:
        decision = LunaLoopDecisionV1.model_validate(payload)
        action, parsed = validate_luna_action_for_principal(decision, "alpha_1")
        assert isinstance(parsed, ActionIntent)
        observed.add(str(action["action_type"]))
    assert observed == set(LUNA_ACTION_TYPES)


def test_luna_structured_kwargs_are_explicit_and_mcp_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _configured_world(tmp_path)
    captured: dict[str, Any] = {}

    async def fake_acall_llm_structured(**kwargs: Any) -> tuple[Any, object]:
        captured.update(kwargs)
        directory = Path(kwargs["working_directory"])
        assert directory.is_dir()
        assert not any(directory.iterdir())
        decision = LunaLoopDecisionV1.model_validate(
            {
                "schema_version": "luna_loop_decision.v1",
                "action": {
                    "action_type": "query_kernel",
                    "query_type": "resources",
                    "params": {"principal_id": "alpha_1"},
                },
            }
        )
        return decision, _llm_result(decision.model_dump_json())

    fake_module = types.ModuleType("llm_client")
    fake_module.acall_llm_structured = fake_acall_llm_structured
    monkeypatch.setitem(sys.modules, "llm_client", fake_module)
    monkeypatch.setattr(
        "agent_ecology3.world.luna_actions.luna_provider_schema_sha256",
        lambda: "0" * 64,
    )
    monkeypatch.setattr(
        "agent_ecology3.world.luna_actions.shared_client_exposes_codex_events",
        lambda: True,
    )
    monkeypatch.delenv("LLM_CLIENT_CODEX_ISOLATE_HOME", raising=False)

    result = asyncio.run(
        world.call_llm_as_syscall_async(
            payer_id="alpha_1",
            model=LUNA_MODEL,
            messages=[{"role": "user", "content": "choose"}],
            tools=World.build_loop_action_tools(),
        )
    )

    assert result["success"] is True
    assert result["structured_action"]["action_type"] == "query_kernel"
    assert LunaLoopDecisionV1.model_validate_json(result["content"])
    assert captured["response_model"] is LunaLoopDecisionV1
    assert captured["reasoning_effort"] == "medium"
    assert captured["codex_transport"] == "cli"
    assert captured["sandbox_mode"] == "read-only"
    assert captured["approval_policy"] == "never"
    assert captured["num_retries"] == 0
    assert captured["fallback_models"] == []
    assert "tools" not in captured
    assert "mcp_servers" not in captured
    assert not Path(captured["working_directory"]).exists()


def test_luna_structured_result_rejects_observed_intrinsic_tool_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _configured_world(tmp_path)
    before_budget = world.ledger.get_llm_budget("alpha_1")

    async def fake_acall_llm_structured(**_kwargs: Any) -> tuple[Any, object]:
        decision = LunaLoopDecisionV1.model_validate(
            {
                "schema_version": "luna_loop_decision.v1",
                "action": {
                    "action_type": "query_kernel",
                    "query_type": "resources",
                    "params": {"principal_id": "alpha_1"},
                },
            }
        )
        result = _llm_result(decision.model_dump_json())
        result.codex_events = [
            {"id": "cmd-1", "type": "command_execution", "status": "completed"}
        ]
        return decision, result

    fake_module = types.ModuleType("llm_client")
    fake_module.acall_llm_structured = fake_acall_llm_structured
    monkeypatch.setitem(sys.modules, "llm_client", fake_module)
    monkeypatch.setattr(
        "agent_ecology3.world.luna_actions.shared_client_exposes_codex_events",
        lambda: True,
    )

    result = asyncio.run(
        world.call_llm_as_syscall_async(
            payer_id="alpha_1",
            model=LUNA_MODEL,
            messages=[{"role": "user", "content": "choose"}],
        )
    )

    assert result["success"] is False
    assert "forbidden intrinsic Codex tool: command_execution" in result["error"]
    assert world.ledger.get_llm_budget("alpha_1") == before_budget


def test_production_loop_consumes_structured_action_without_json_or_tool_fallback(
    tmp_path: Path,
) -> None:
    world = _configured_world(tmp_path, bootstrap_loop_llm=True)
    world.config.llm.loop_forced_explore_mode = "off"

    def fake_syscall(**_kwargs: Any) -> dict[str, Any]:
        return {
            "success": True,
            "trace_id": "ae3/test_luna_structured/event_1/payer/alpha_1",
            "content": (
                '{"schema_version":"luna_loop_decision.v1","action":'
                '{"action_type":"query_kernel","query_type":"resources",'
                '"params":{"principal_id":"alpha_1"}}}'
            ),
            "structured_action": {
                "action_type": "query_kernel",
                "query_type": "resources",
                "params": {"principal_id": "alpha_1"},
            },
            "tool_calls": [],
        }

    world.call_llm_as_syscall = fake_syscall  # type: ignore[method-assign]
    result = world.execute_action_data(
        "alpha_1",
        {
            "action_type": "invoke_artifact",
            "artifact_id": "alpha_1_loop",
            "method": "run",
            "args": [],
        },
    )

    assert result.success is True
    decisions = [
        event
        for event in world.logger.read_recent(50)
        if event.get("event_type") == "loop_decision"
    ]
    assert decisions[-1]["llm_action_source"] == "structured_output"
    assert decisions[-1]["decision_action"] == "query_kernel"
    assert decisions[-1]["gate_fallback_used"] is False


def test_luna_dispatch_rejects_disabled_home_isolation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _configured_world(tmp_path)
    monkeypatch.setenv("LLM_CLIENT_CODEX_ISOLATE_HOME", "0")
    fake_module = types.ModuleType("llm_client")

    async def unexpected(**_kwargs: Any) -> tuple[Any, object]:
        raise AssertionError("provider boundary should not be entered")

    fake_module.acall_llm_structured = unexpected
    monkeypatch.setitem(sys.modules, "llm_client", fake_module)
    monkeypatch.setattr(
        "agent_ecology3.world.luna_actions.shared_client_exposes_codex_events",
        lambda: True,
    )
    result = asyncio.run(
        world.call_llm_as_syscall_async(
            payer_id="alpha_1",
            model=LUNA_MODEL,
            messages=[{"role": "user", "content": "choose"}],
        )
    )
    assert result["success"] is False
    assert "requires LLM_CLIENT_CODEX_ISOLATE_HOME" in result["error"]


def test_luna_dispatch_is_inaccessible_without_public_intrinsic_event_custody(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = _configured_world(tmp_path)
    before_budget = world.ledger.get_llm_budget("alpha_1")
    monkeypatch.setattr(
        "agent_ecology3.world.luna_actions.shared_client_exposes_codex_events",
        lambda: False,
    )

    result = world.call_llm_as_syscall(
        payer_id="alpha_1",
        model=LUNA_MODEL,
        messages=[{"role": "user", "content": "choose"}],
    )

    assert result["success"] is False
    assert result["error_code"] == "intrinsic_codex_events_not_public"
    assert world.ledger.get_llm_budget("alpha_1") == before_budget


def test_luna_dispatch_revalidates_mutated_profile_before_reservation(
    tmp_path: Path,
) -> None:
    world = _configured_world(tmp_path)
    before_budget = world.ledger.get_llm_budget("alpha_1")
    world.config.llm.reasoning_effort = "low"

    result = world.call_llm_as_syscall(
        payer_id="alpha_1",
        model=LUNA_MODEL,
        messages=[{"role": "user", "content": "choose"}],
    )

    assert result["success"] is False
    assert result["error_code"] == "invalid_luna_profile"
    assert world.ledger.get_llm_budget("alpha_1") == before_budget


def test_prompt_schema_profile_is_ambient_free_and_observes_tool_event_custody() -> None:
    report = build_provider_free_preflight(llm_client_repo=LLM_CLIENT_REPO)

    assert report.shared_client_revision == REVIEWED_LLM_CLIENT_REVISION
    assert report.action_branch_count == 6
    assert report.provider_schema_has_open_object is False
    assert report.working_directory_empty is True
    assert report.inherited_mcp_servers == []
    assert report.command_uses_stdin_prompt is True
    assert report.command_uses_output_schema is True
    assert report.structured_kwargs_omit_tools is True
    assert report.structured_kwargs_omit_mcp_servers is True
    assert report.intrinsic_event_contract["public_codex_event_types"] == [
        "command_execution",
        "file_change",
        "web_search",
        "mcp_tool_call",
    ]
    assert report.intrinsic_event_contract["public_tool_call_names"] == ["probe_tool"]
    assert report.intrinsic_tool_events_observable is True
    assert report.status == "pass"
    assert report.blocker_owner is None
    assert report.blocker_code is None
    assert "gpt-5.6-luna" in report.command
    assert 'model_reasoning_effort="medium"' in report.command
    assert report.command[report.command.index("-s") + 1] == "read-only"
    assert "ae3_action" not in "\n".join(
        message["content"] for message in report.prompt_messages
    )


def test_luna_config_file_is_exact_profile() -> None:
    config = load_config("config/config.luna_recovery_gate.yaml")
    assert config.llm == LLMConfig(
        **_luna_profile(),
        timeout_seconds=90,
        agent_max_turns=1,
        model_justification=(
            "Plan 10 qualifies one bounded AE3 action through the exact Luna "
            "subscription route."
        ),
    )
