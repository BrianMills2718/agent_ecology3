"""Resident agents: kernel action endpoint and MCP forwarding (provider-free)."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_ecology3.config import AppConfig
from agent_ecology3.mcp import loop_action_server
from agent_ecology3.simulation.resident import (
    AE3_TOOL_NAME,
    ResidentKernel,
    agent_call_kwargs,
)
from agent_ecology3.world import World

BANK = Path(__file__).resolve().parents[1] / "config" / "tasks" / "humaneval_plan24_v1.jsonl"


def _kernel(tmp_path: Path, actions_per_turn: int = 2) -> tuple[World, ResidentKernel, TestClient]:
    cfg = AppConfig()
    cfg.principals.count = 2
    cfg.llm.enable_bootstrap_loop_llm = False
    cfg.dashboard.enabled = False
    cfg.logging.logs_dir = str(tmp_path / "logs")
    cfg.mint.mode = "task_bounty"
    cfg.mint.task_bank_path = str(BANK)
    world = World(AppConfig.model_validate(cfg.model_dump()), run_id="resident_test")
    kernel = ResidentKernel(world, tmp_path / "agents", actions_per_turn=actions_per_turn)
    app = FastAPI()
    kernel.install_routes(app)
    return world, kernel, TestClient(app)


def _write(content: str = "x") -> dict[str, Any]:
    return {"action_type": "write_artifact", "artifact_id": "alpha_1_note", "artifact_type": "note", "content": content}


def test_endpoint_executes_action_and_returns_real_result(tmp_path: Path) -> None:
    world, kernel, client = _kernel(tmp_path)
    token = kernel.agents["alpha_1"].token
    response = client.post("/agent-act/alpha_1", json=_write(), headers={"Authorization": f"Bearer {token}"})
    body = response.json()
    assert response.status_code == 200 and body["success"] is True
    assert world.artifacts.get("alpha_1_note") is not None
    events = [e for e in world.logger.read_recent(100) if e.get("event_type") == "resident_action"]
    assert events and events[-1]["principal_id"] == "alpha_1" and events[-1]["success"] is True


def test_endpoint_rejects_wrong_token_and_cross_identity(tmp_path: Path) -> None:
    _, kernel, client = _kernel(tmp_path)
    other = kernel.agents["alpha_2"].token
    assert client.post("/agent-act/alpha_1", json=_write(), headers={"Authorization": f"Bearer {other}"}).status_code == 403
    assert client.post("/agent-act/alpha_1", json=_write(), headers={"Authorization": "Bearer nope"}).status_code == 403


def test_endpoint_enforces_actions_per_turn(tmp_path: Path) -> None:
    _, kernel, client = _kernel(tmp_path, actions_per_turn=1)
    headers = {"Authorization": f"Bearer {kernel.agents['alpha_1'].token}"}
    assert client.post("/agent-act/alpha_1", json=_write("a"), headers=headers).json()["success"] is True
    second = client.post("/agent-act/alpha_1", json=_write("b"), headers=headers).json()
    assert second["success"] is False and second["error_code"] == "turn_action_limit"


def test_mcp_tool_forwards_to_kernel_with_launch_identity(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    class _Response(io.BytesIO):
        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

    def fake_urlopen(request: Any, timeout: int) -> _Response:
        captured["url"] = request.full_url
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.data)
        return _Response(json.dumps({"success": True, "message": "ok"}).encode())

    monkeypatch.setenv("AE3_KERNEL_URL", "http://127.0.0.1:9999")
    monkeypatch.setenv("AE3_PRINCIPAL_ID", "alpha_2")
    monkeypatch.setenv("AE3_AGENT_TOKEN", "tok")
    monkeypatch.setattr(loop_action_server.urllib.request, "urlopen", fake_urlopen)
    result = loop_action_server.ae3_action(action_type="read_artifact", artifact_id="alpha_1_task_28")
    assert result == {"success": True, "message": "ok"}
    assert captured["url"] == "http://127.0.0.1:9999/agent-act/alpha_2"
    assert captured["auth"] == "Bearer tok"
    assert captured["body"] == {"action_type": "read_artifact", "artifact_id": "alpha_1_task_28"}


def test_mcp_tool_keeps_legacy_echo_without_kernel(monkeypatch: Any) -> None:
    monkeypatch.delenv("AE3_KERNEL_URL", raising=False)
    assert loop_action_server.ae3_action(action_type="query_kernel", query_type="mint") == {
        "ok": True,
        "action": {"action_type": "query_kernel", "query_type": "mint"},
    }


def test_agent_options_allow_only_the_ae3_tool_and_resume(tmp_path: Path) -> None:
    _, kernel, _ = _kernel(tmp_path)
    agent = kernel.agents["alpha_1"]
    first = agent_call_kwargs(agent, "http://k", max_turns=6)
    assert first["allowed_tools"] == [AE3_TOOL_NAME] and first["tools"] == []
    assert first["strict_mcp_config"] is True and "Bash" in first["disallowed_tools"]
    assert "resume" not in first
    assert first["mcp_servers"]["ae3"]["env"]["AE3_PRINCIPAL_ID"] == "alpha_1"
    agent.session_id = "sess-1"
    assert agent_call_kwargs(agent, "http://k", max_turns=6)["resume"] == "sess-1"


def test_codex_options_use_persistent_home_with_preapproved_ae3_server(tmp_path: Path) -> None:
    from agent_ecology3.simulation.resident import codex_call_kwargs

    _, kernel, _ = _kernel(tmp_path)
    agent = kernel.agents["alpha_1"]
    first = codex_call_kwargs(agent, "http://k", reasoning_effort="low")
    home = Path(first["codex_home"])
    assert home == agent.workdir / "codex_home" and (home / ".codex").is_dir()
    config = (home / ".codex" / "config.toml").read_text()
    assert '[mcp_servers."ae3"]\ndefault_tools_approval_mode = "approve"' in config
    assert first["codex_session_mode"] == "fresh" and first["agent_hard_timeout"] == 0
    sessions = home / ".codex" / "sessions"
    assert sessions.is_dir() and not sessions.is_symlink(), "agent sessions must not link to the user's Codex history"
    assert first["sandbox_mode"] == "read-only" and first["approval_policy"] == "never"
    agent.session_id = "01a10e02-68dc-77c1-a2a0-fe1b6de6b883"
    again = codex_call_kwargs(agent, "http://k", reasoning_effort="low")
    assert again["codex_session_mode"] == "resume" and again["codex_session_id"] == agent.session_id
    assert again["codex_home"] == first["codex_home"]


def test_shell_command_counter_reads_llm_client_codex_item_shape() -> None:
    """llm_client returns completed Codex items directly (item["type"]), not wrapped."""
    from agent_ecology3.simulation.resident import count_shell_commands

    items = [
        {"type": "reasoning", "text": "plan"},
        {"type": "command_execution", "command": "python -c 'print(1)'"},
        {"type": "mcp_tool_call", "server": "ae3", "tool": "ae3_action"},
        {"type": "commandExecution", "command": "pytest -q"},
    ]
    assert count_shell_commands(items) == 2
    assert count_shell_commands([]) == 0
