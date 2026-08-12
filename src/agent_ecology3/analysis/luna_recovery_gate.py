"""Provider-free Slice A preflight for the Plan 10 Luna decision route."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from ..config import AppConfig, load_config
from ..world.luna_actions import (
    LUNA_ACTION_TYPES,
    LUNA_MODEL,
    LunaLoopDecisionV1,
    luna_provider_schema,
    luna_provider_schema_sha256,
)
from ..world.world import World

REVIEWED_LLM_CLIENT_REVISION = "286715784f1d535d6dfcd2c867ca678d666e27d5"


class _StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LunaPreflightV1(_StrictContract):
    schema_version: Literal["luna_preflight.v1"] = "luna_preflight.v1"
    status: Literal["pass", "blocked"]
    blocker_code: str | None
    blocker_owner: str | None
    blocker_reason: str | None
    model: str
    reasoning_effort: str
    transport: str
    sandbox_mode: str
    approval_policy: str
    retry_count: int
    fallback_models: list[str]
    response_model: str
    action_types: list[str]
    action_branch_count: int
    provider_schema_sha256: str
    provider_schema: dict[str, Any]
    provider_schema_has_open_object: bool
    prompt_messages: list[dict[str, str]]
    working_directory_empty: bool
    codex_home_isolated: bool
    codex_home_source: str
    codex_home_config_sha256: str
    inherited_mcp_servers: list[str]
    command: list[str]
    command_uses_stdin_prompt: bool
    command_uses_output_schema: bool
    structured_kwargs_omit_tools: bool
    structured_kwargs_omit_mcp_servers: bool
    intrinsic_tool_events_observable: bool
    intrinsic_event_contract: dict[str, Any]
    shared_client_revision: str | None


def _luna_config() -> AppConfig:
    cfg = AppConfig()
    cfg.llm.default_model = LUNA_MODEL
    cfg.llm.allowed_models = [LUNA_MODEL]
    cfg.llm.num_retries = 0
    cfg.llm.agent_cwd = None
    cfg.llm.decision_output_mode = "luna_structured_v1"
    cfg.llm.reasoning_effort = "medium"
    cfg.llm.codex_transport = "cli"
    cfg.llm.codex_sandbox_mode = "read-only"
    cfg.llm.codex_approval_policy = "never"
    cfg.llm.codex_isolate_home = True
    cfg.llm.structured_response_model = "LunaLoopDecisionV1"
    cfg.llm.expected_billing_mode = "subscription_included"
    return AppConfig.model_validate(cfg.model_dump())


def _contains_open_object(node: Any) -> bool:
    if isinstance(node, dict):
        if node.get("type") == "object" and node.get("additionalProperties") is not False:
            return True
        return any(_contains_open_object(value) for value in node.values())
    if isinstance(node, list):
        return any(_contains_open_object(value) for value in node)
    return False


def _action_branches(schema: dict[str, Any]) -> list[dict[str, Any]]:
    action = schema.get("properties", {}).get("action", {})
    branches = action.get("anyOf", []) if isinstance(action, dict) else []
    return [branch for branch in branches if isinstance(branch, dict)]


def _git_revision(repo_root: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    revision = completed.stdout.strip()
    return revision if completed.returncode == 0 and revision else None


def _codex_home_inventory(config_text: str) -> list[str]:
    servers: list[str] = []
    for line in config_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[mcp_servers."):
            servers.append(stripped)
    return servers


def _probe_shared_client_event_contract() -> dict[str, Any]:
    """Exercise the CLI event parser with intrinsic and MCP item fixtures."""

    from llm_client.sdk.agents_codex import (
        _extract_codex_cli_completed_items,
        _extract_codex_cli_tool_calls,
        _result_from_codex_cli,
        parse_codex_exec_events,
    )

    intrinsic_types = ["command_execution", "file_change", "web_search"]
    items: list[dict[str, Any]] = [
        {"id": f"probe-{item_type}", "type": item_type, "status": "completed"}
        for item_type in intrinsic_types
    ]
    items.append(
        {
            "id": "probe-mcp",
            "type": "mcp_tool_call",
            "server": "probe",
            "tool": "probe_tool",
            "arguments": {},
            "status": "completed",
        }
    )
    stdout_jsonl = "\n".join(
        json.dumps({"type": "item.completed", "item": item}) for item in items
    )
    codex_events = _extract_codex_cli_completed_items(stdout_jsonl)
    tool_calls = _extract_codex_cli_tool_calls(stdout_jsonl)
    session = parse_codex_exec_events(stdout_jsonl, "")
    result = _result_from_codex_cli(
        LUNA_MODEL,
        '{"schema_version":"luna_loop_decision.v1"}',
        transport="codex_cli",
        session=session,
        tool_calls=tool_calls,
        codex_events=codex_events,
    )
    raw = result.raw_response if isinstance(result.raw_response, dict) else {}
    serialized = json.dumps(
        {
            "codex_events": result.codex_events,
            "tool_calls": result.tool_calls,
            "raw_response": raw,
        },
        sort_keys=True,
    )
    missing = [item_type for item_type in intrinsic_types if item_type not in serialized]
    return {
        "fixture_item_types": [*intrinsic_types, "mcp_tool_call"],
        "public_tool_call_names": [
            str(call.get("function", {}).get("name", ""))
            for call in result.tool_calls
            if isinstance(call, dict)
        ],
        "public_codex_event_types": [
            str(event.get("type", ""))
            for event in result.codex_events
            if isinstance(event, dict)
        ],
        "public_raw_response_keys": sorted(str(key) for key in raw),
        "missing_intrinsic_item_types": missing,
        "all_intrinsic_item_types_observable": not missing,
    }


def _portable_command(command: list[str], workspace: str) -> list[str]:
    rendered = [
        entry.replace(workspace, "<empty-decision-workspace>") for entry in command
    ]
    if rendered:
        rendered[0] = "<codex-cli>"
    return rendered


def build_provider_free_preflight(
    *,
    llm_client_repo: str | Path,
) -> LunaPreflightV1:
    """Compile the exact command/profile inventory without executing Codex."""

    from llm_client.sdk.agents import _messages_to_agent_prompt
    from llm_client.sdk.agents_codex import (
        _build_codex_cli_command,
        _create_codex_home,
    )

    cfg = _luna_config()
    schema = luna_provider_schema()
    branches = _action_branches(schema)
    world = object.__new__(World)
    world.config = cfg
    world.run_id = "plan10_provider_free_preflight"
    world._loop_prompt_template_cache = None
    messages = world.build_loop_messages(
        principal_id="alpha_1",
        state_snapshot={
            "balance": 100,
            "resources": {"llm_budget": 1.0, "disk_available": 100_000},
            "artifacts": [],
            "memory": {"next_objective": "discover ecosystem artifacts"},
            "recent_feedback": {"actions_attempted": 0, "recent_error_codes": []},
        },
        strategy_text="",
    )
    prompt, system_prompt = _messages_to_agent_prompt(messages)
    if system_prompt:
        prompt = f"{system_prompt}\n\n{prompt}"

    client_root = Path(llm_client_repo).resolve()
    client_revision = _git_revision(client_root)
    isolated_home: str | None = None
    with tempfile.TemporaryDirectory(prefix="ae3_luna_preflight_workspace_") as workspace:
        workspace_path = Path(workspace)
        structured_kwargs = world._luna_structured_call_kwargs(
            model=LUNA_MODEL,
            messages=messages,
            trace_id="plan10/provider-free/preflight",
            working_directory=workspace,
        )
        isolated_home = _create_codex_home({})
        try:
            home_config = (Path(isolated_home) / ".codex" / "config.toml").read_text(
                encoding="utf-8"
            )
            command, _env, stdin_payload = _build_codex_cli_command(
                LUNA_MODEL,
                prompt,
                output_schema=schema,
                kwargs={
                    **structured_kwargs,
                    "model_reasoning_effort": structured_kwargs["reasoning_effort"],
                    "codex_home": isolated_home,
                },
                output_path=str(workspace_path / "last_message.txt"),
                schema_path=str(workspace_path / "output_schema.json"),
            )
            workspace_empty = not any(workspace_path.iterdir())
            command_inventory = _portable_command(command, workspace)
            inherited_mcp = _codex_home_inventory(home_config)
            event_contract = _probe_shared_client_event_contract()
            intrinsic_observable = bool(
                event_contract["all_intrinsic_item_types_observable"]
            )
            profile_ok = (
                len(branches) == len(LUNA_ACTION_TYPES)
                and not _contains_open_object(schema)
                and workspace_empty
                and not inherited_mcp
                and "--output-schema" in command_inventory
                and "tools" not in structured_kwargs
                and "mcp_servers" not in structured_kwargs
            )
            status: Literal["pass", "blocked"] = (
                "pass" if profile_ok and intrinsic_observable else "blocked"
            )
            blocker_code = None
            blocker_owner = None
            blocker_reason = None
            if not profile_ok:
                blocker_code = "luna_profile_inventory_failed"
                blocker_owner = "agent_ecology3"
                blocker_reason = (
                    "The provider-free route inventory did not retain the exact closed "
                    "schema, empty workspace, MCP-free kwargs/home, and CLI schema flag."
                )
            elif not intrinsic_observable:
                blocker_code = "intrinsic_codex_events_not_public"
                blocker_owner = "llm_client"
                blocker_reason = (
                    "The shared Codex CLI result retains only MCP tool calls and a "
                    "transport summary; command, file-change, and web/search item events "
                    "are not exposed, so AE3 cannot prove that intrinsic Codex tools "
                    "executed zero times."
                )

            return LunaPreflightV1(
                status=status,
                blocker_code=blocker_code,
                blocker_owner=blocker_owner,
                blocker_reason=blocker_reason,
                model=LUNA_MODEL,
                reasoning_effort="medium",
                transport="cli",
                sandbox_mode="read-only",
                approval_policy="never",
                retry_count=0,
                fallback_models=[],
                response_model=LunaLoopDecisionV1.__name__,
                action_types=list(LUNA_ACTION_TYPES),
                action_branch_count=len(branches),
                provider_schema_sha256=luna_provider_schema_sha256(),
                provider_schema=schema,
                provider_schema_has_open_object=_contains_open_object(schema),
                prompt_messages=messages,
                working_directory_empty=workspace_empty,
                codex_home_isolated=True,
                codex_home_source="shared config and auth projected without ambient MCP tables",
                codex_home_config_sha256=hashlib.sha256(
                    home_config.encode("utf-8")
                ).hexdigest(),
                inherited_mcp_servers=inherited_mcp,
                command=command_inventory,
                command_uses_stdin_prompt=command_inventory[-1] == "-"
                and bool(stdin_payload),
                command_uses_output_schema="--output-schema" in command_inventory,
                structured_kwargs_omit_tools="tools" not in structured_kwargs,
                structured_kwargs_omit_mcp_servers="mcp_servers" not in structured_kwargs,
                intrinsic_tool_events_observable=intrinsic_observable,
                intrinsic_event_contract=event_contract,
                shared_client_revision=client_revision,
            )
        finally:
            # Real calls clean this helper-owned directory internally. The
            # provider-free direct helper probe must do so itself.
            shutil.rmtree(isolated_home, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None)
    parser.add_argument("--llm-client-repo", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    if args.config is not None:
        # Validate the supplied production profile before compiling the shared
        # route inventory. No call is dispatched by this module.
        load_config(args.config)
    report = build_provider_free_preflight(llm_client_repo=args.llm_client_repo)
    rendered = report.model_dump_json(indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report.status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
