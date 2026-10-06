"""Resident agents: kernel action endpoint and MCP forwarding (provider-free)."""

from __future__ import annotations

import asyncio
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
    assert first["sandbox_mode"] == "workspace-write" and first["approval_policy"] == "never"
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


def _history(home: Path, items: list[dict[str, Any]]) -> None:
    import sqlite3

    (home / ".codex").mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(home / ".codex" / "thread_history_1.sqlite")
    con.execute("create table thread_items (item_json text)")
    con.executemany("insert into thread_items values (?)", [(json.dumps(i),) for i in items])
    con.commit()
    con.close()


def test_shell_commands_are_counted_from_codex_history(tmp_path: Path) -> None:
    from agent_ecology3.simulation.resident import history_shell_commands

    _history(tmp_path, [{"type": "reasoning"}, {"type": "commandExecution"},
                        {"type": "mcpToolCall"}, {"type": "command_execution"}])
    assert history_shell_commands(tmp_path) == 2
    assert history_shell_commands(tmp_path / "missing") == 0


def test_trim_keeps_thread_history_and_removes_bulk(tmp_path: Path) -> None:
    from agent_ecology3.simulation.resident import trim_codex_home

    _history(tmp_path, [{"type": "reasoning"}])
    base = tmp_path / ".codex"
    for name in ("plugins", "cache", ".tmp"):
        (base / name).mkdir()
        (base / name / "f").write_text("x")
    (base / "state_5.sqlite").write_text("x")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text("keep")
    (base / "sessions_link").symlink_to(outside, target_is_directory=True)
    trim_codex_home(tmp_path)
    assert (base / "thread_history_1.sqlite").is_file()
    assert not any((base / n).exists() for n in ("plugins", "cache", ".tmp", "state_5.sqlite"))
    assert (outside / "keep").is_file()


def test_codex_writable_folder_does_not_contain_its_codex_home(tmp_path: Path) -> None:
    """The agent may write in its working folder; its Codex config and token must not be there."""
    from agent_ecology3.simulation.resident import codex_call_kwargs

    _, kernel, _ = _kernel(tmp_path)
    kwargs = codex_call_kwargs(kernel.agents["alpha_1"], "http://k", reasoning_effort="low")
    work = Path(kwargs["working_directory"]).resolve()
    home = Path(kwargs["codex_home"]).resolve()
    assert work != home and work not in home.parents, (work, home)


def test_turn_records_measured_duration_without_model_usage(tmp_path: Path) -> None:
    """Codex results carry no duration_ms; plan25_codeflow_run3 logged null on every turn."""
    from types import SimpleNamespace

    from agent_ecology3.simulation.resident import run_agent_turn

    world, kernel, _ = _kernel(tmp_path)

    async def fake_acall_llm(*_args: Any, **_kwargs: Any) -> Any:
        await asyncio.sleep(0.05)
        return SimpleNamespace(usage={"session_id": "s1"}, raw_response=None, codex_events=[], tool_calls=[],
                               content="done", finish_reason="stop", cost=None, cost_source=None)

    asyncio.run(run_agent_turn(kernel, kernel.agents["alpha_1"], model="codex/test", kernel_url="http://k",
                               run_id="r", acall_llm=fake_acall_llm))
    turns = [e for e in world.logger.read_recent(50) if e.get("event_type") == "resident_turn"]
    assert len(turns) == 1 and isinstance(turns[0]["duration_ms"], int) and turns[0]["duration_ms"] >= 50


def test_new_codex_home_drops_copied_plugins_and_cache(tmp_path: Path) -> None:
    """plan25_codeflow_run3: 16 agents carried ~130 MB each of copied plugins/cache during the run."""
    from agent_ecology3.simulation.resident import codex_call_kwargs

    _, kernel, _ = _kernel(tmp_path)
    home = Path(codex_call_kwargs(kernel.agents["alpha_1"], "http://k", reasoning_effort="low")["codex_home"])
    assert (home / ".codex" / "config.toml").is_file()
    assert not (home / ".codex" / "plugins").exists() and not (home / ".codex" / "cache").exists()
    import tomllib

    features = tomllib.loads((home / ".codex" / "config.toml").read_text())["features"]
    assert features["plugins"] is False and features["remote_plugin"] is False
    size = sum(f.stat().st_size for f in home.rglob("*") if f.is_file() and not f.is_symlink())
    assert size < 20_000_000, size


def test_codex_plugin_features_are_disabled_with_or_without_features_table() -> None:
    """Codex re-synced ~156 MB of plugins per session start (plan25_disk_probe2)."""
    import tomllib

    from agent_ecology3.simulation.resident import _disable_codex_features

    for config in ('model = "x"\n[features]\nprevent_idle_sleep = true\n[other]\na = 1\n', 'model = "x"\n'):
        features = tomllib.loads(_disable_codex_features(config))["features"]
        assert features["plugins"] is False and features["remote_plugin"] is False


def test_send_message_is_delivered_once_at_the_recipients_next_turn(tmp_path: Path) -> None:
    world, kernel, client = _kernel(tmp_path)
    a1, a2 = kernel.agents["alpha_1"], kernel.agents["alpha_2"]
    kernel.turn = 3
    sent = client.post("/agent-act/alpha_1", headers={"Authorization": f"Bearer {a1.token}"},
                       json={"action_type": "send_message", "recipient_id": "alpha_2",
                             "content": "your gcd helper fails on 0"}).json()
    assert sent["success"] is True and a1.actions_this_turn == 1
    events = [e for e in world.logger.read_recent(50) if e.get("event_type") == "agent_message"]
    assert [(e["principal_id"], e["recipient"], e["text"], e["turn"]) for e in events] == [
        ("alpha_1", "alpha_2", "your gcd helper fails on 0", 3)]
    first = kernel.observation(a2)
    assert "Messages to you since your last turn:\n- from alpha_1 (turn 3): your gcd helper fails on 0" in first
    assert "Messages to you" not in kernel.observation(a2)  # shown once
    assert "Messages to you" not in kernel.observation(a1)


def test_send_message_refuses_bad_recipient_and_empty_text(tmp_path: Path) -> None:
    world, kernel, client = _kernel(tmp_path, actions_per_turn=4)
    a1 = kernel.agents["alpha_1"]
    headers = {"Authorization": f"Bearer {a1.token}"}
    for payload, code in (({"recipient_id": "alpha_1", "content": "hi"}, "invalid_recipient"),
                          ({"recipient_id": "nobody", "content": "hi"}, "invalid_recipient"),
                          ({"recipient_id": "alpha_2", "content": "  "}, "empty_message")):
        out = client.post("/agent-act/alpha_1", headers=headers, json={"action_type": "send_message", **payload}).json()
        assert out["success"] is False and out["error_code"] == code
    assert not [e for e in world.logger.read_recent(50) if e.get("event_type") == "agent_message"]
    assert kernel.agents["alpha_2"].inbox == []


def _route_mcp_tool_to(client: TestClient, monkeypatch: Any, principal_id: str, token: str) -> None:
    """Send the real ae3_action tool's HTTP request into the in-process kernel."""

    class _Response(io.BytesIO):
        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

    def urlopen_into_kernel(request: Any, timeout: int) -> _Response:
        path = "/" + request.full_url.split("/", 3)[3]
        response = client.post(path, content=request.data, headers=dict(request.header_items()))
        return _Response(response.content)

    monkeypatch.setenv("AE3_KERNEL_URL", "http://kernel.test")
    monkeypatch.setenv("AE3_PRINCIPAL_ID", principal_id)
    monkeypatch.setenv("AE3_AGENT_TOKEN", token)
    monkeypatch.setattr(loop_action_server.urllib.request, "urlopen", urlopen_into_kernel)


def test_agent_sets_read_price_through_the_tool_and_another_agent_pays_it(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """Plan 26: the rules said agents may set read_price, but the tool had no field for it."""
    world, kernel, client = _kernel(tmp_path, actions_per_turn=4)
    a1, a2 = kernel.agents["alpha_1"], kernel.agents["alpha_2"]
    _route_mcp_tool_to(client, monkeypatch, "alpha_1", a1.token)
    wrote = loop_action_server.ae3_action(
        action_type="write_artifact", artifact_id="alpha_1_gcd", artifact_type="solution:demo/gcd",
        content="def gcd(a, b):\n    return a if b == 0 else gcd(b, a % b)\n", read_price=5,
    )
    assert wrote["success"] is True, wrote
    assert world.artifacts.get("alpha_1_gcd").read_price == 5
    # Rewriting the code without a price keeps the posted price.
    rewrote = loop_action_server.ae3_action(
        action_type="write_artifact", artifact_id="alpha_1_gcd", artifact_type="solution:demo/gcd",
        content="import math\ngcd = math.gcd\n",
    )
    assert rewrote["success"] is True and world.artifacts.get("alpha_1_gcd").read_price == 5
    refused = loop_action_server.ae3_action(
        action_type="write_artifact", artifact_id="alpha_1_gcd", artifact_type="solution:demo/gcd",
        content="x", read_price=-1,
    )
    assert refused["success"] is False and world.artifacts.get("alpha_1_gcd").read_price == 5

    before = {p: world.ledger.get_scrip(p) for p in ("alpha_1", "alpha_2")}
    _route_mcp_tool_to(client, monkeypatch, "alpha_2", a2.token)
    bought = loop_action_server.ae3_action(action_type="read_artifact", artifact_id="alpha_1_gcd")
    assert bought["success"] is True and bought["data"]["read_price_paid"] == 5
    assert world.ledger.get_scrip("alpha_2") == before["alpha_2"] - 5
    assert world.ledger.get_scrip("alpha_1") == before["alpha_1"] + 5
    reads = [e for e in world.logger.read_recent(100) if e.get("event_type") == "artifact_read"]
    assert [(e["principal_id"], e["recipient"], e["read_price_paid"]) for e in reads] == [("alpha_2", "alpha_1", 5)]


def test_observation_lists_every_unclaimed_task_in_a_365_task_bank(tmp_path: Path) -> None:
    """Plan 26 gap: one 200-row listing showed 195 of 365 tasks and no later solutions."""
    import re
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.run_recoverable_evaluation import _seed_task_bank

    owners = [f"alpha_{i}" for i in range(1, 9)]
    bank = tmp_path / "bank.jsonl"
    bank.write_text("".join(
        json.dumps({"task_id": f"synthetic/{n}", "owner": owners[n % 8], "entry_point": f"f{n}",
                    "prompt": f"def f{n}(x):\n    \"\"\"Return x.\"\"\"\n", "test": "def check(c):\n    assert c(1) == 1\n"}) + "\n"
        for n in range(365)
    ), encoding="utf-8")
    cfg = AppConfig()
    cfg.principals.count = 8
    cfg.llm.enable_bootstrap_loop_llm = False
    cfg.dashboard.enabled = False
    cfg.logging.logs_dir = str(tmp_path / "logs")
    cfg.mint.mode = "task_bounty"
    cfg.mint.task_bank_path = str(bank)
    world = World(AppConfig.model_validate(cfg.model_dump()), run_id="listing_test")
    ids = _seed_task_bank(world, bank)
    assert len(ids) == 365
    world.artifacts.get(ids[0]).metadata["bounty_claimed_by"] = "alpha_2"
    for n in range(70):  # more agent artifacts than the listing shows
        world.artifacts.write(f"alpha_3_sol_{n}", f"solution:synthetic/{n}", "x", created_by="alpha_3", read_price=n % 3)
    kernel = ResidentKernel(world, tmp_path / "agents", actions_per_turn=4)
    text = kernel.observation(kernel.agents["alpha_1"])

    def listed(artifact_id: str) -> bool:
        return re.search(rf"(?<![\w]){re.escape(artifact_id)}(?![\w])", text) is not None

    assert [i for i in ids[1:] if not listed(i)] == [], "an unclaimed task is missing from the observation"
    assert not listed(ids[0]), "a claimed task should be counted, not listed"
    assert "Unclaimed tasks: 364 of 365 (1 already claimed" in text
    assert listed("alpha_3_sol_69") and listed("alpha_3_sol_10") and not listed("alpha_3_sol_9")
    assert "(10 older ones not shown; page through every artifact with query_kernel" in text
    assert len(text) < 20_000, len(text)
