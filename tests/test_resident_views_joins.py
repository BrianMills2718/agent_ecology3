"""Feed and matrix joins over real resident-kernel events (Plan 26 model gaps); no model calls.

Each test drives the in-process kernel through its HTTP /agent-act endpoint,
then projects the events it actually logged, so field names and join keys are
the kernel's own, not hand-written fixtures.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_ecology3.config import AppConfig
from agent_ecology3.dashboard.server import (
    VIEW_EVENT_LIMIT,
    _agent_graph,
    _resident_action_rows,
    create_app,
)
from agent_ecology3.simulation.resident import ResidentKernel
from agent_ecology3.world import World

BANK = Path(__file__).resolve().parents[1] / "config" / "tasks" / "humaneval_plan24_v1.jsonl"


def _kernel(tmp_path: Path, actions_per_turn: int = 4) -> tuple[World, ResidentKernel, TestClient]:
    cfg = AppConfig()
    cfg.principals.count = 3
    cfg.llm.enable_bootstrap_loop_llm = False
    cfg.dashboard.enabled = False
    cfg.logging.logs_dir = str(tmp_path / "logs")
    cfg.mint.mode = "task_bounty"
    cfg.mint.task_bank_path = str(BANK)
    world = World(AppConfig.model_validate(cfg.model_dump()), run_id="views_test")
    kernel = ResidentKernel(world, tmp_path / "agents", actions_per_turn=actions_per_turn)
    app = FastAPI()
    kernel.install_routes(app)
    return world, kernel, TestClient(app)


def _act(client: TestClient, kernel: ResidentKernel, who: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"/agent-act/{who}", json=payload,
                           headers={"Authorization": f"Bearer {kernel.agents[who].token}"})
    body: dict[str, Any] = response.json()
    return body


def _events(world: World) -> list[dict[str, Any]]:
    return world.logger.read_recent(VIEW_EVENT_LIMIT)


def test_two_messages_in_one_turn_each_show_their_own_text(tmp_path: Path) -> None:
    """send_message does not advance event_number; the feed joined on it and showed the first text twice."""
    world, kernel, client = _kernel(tmp_path)
    assert _act(client, kernel, "alpha_1", {"action_type": "send_message", "recipient_id": "alpha_2",
                                           "content": "first"})["success"] is True
    assert _act(client, kernel, "alpha_1", {"action_type": "send_message", "recipient_id": "alpha_3",
                                           "content": "second"})["success"] is True
    events = _events(world)
    numbers = {e["event_number"] for e in events if e.get("event_type") == "agent_message"}
    assert len(numbers) == 1, "precondition: both messages share one event number"
    rows = [r for r in _resident_action_rows(events, {}) if r["action"] == "send_message"]
    assert [(r["description"], r["counterparty"]) for r in rows] == [
        ("messaged alpha_2: “first”", "alpha_2"),
        ("messaged alpha_3: “second”", "alpha_3"),
    ]


def test_logs_without_action_ids_pair_messages_in_order() -> None:
    """Runs recorded before the per-action id still label each message correctly."""
    events = [
        {"sequence": 1, "event_type": "agent_message", "event_number": 4, "principal_id": "alpha_1",
         "recipient": "alpha_2", "text": "first"},
        {"sequence": 2, "event_type": "resident_action", "event_number": 4, "principal_id": "alpha_1",
         "action_type": "send_message", "success": True},
        {"sequence": 3, "event_type": "resident_action", "event_number": 4, "principal_id": "alpha_1",
         "action_type": "send_message", "success": False, "error_code": "empty_message"},
        {"sequence": 4, "event_type": "agent_message", "event_number": 4, "principal_id": "alpha_1",
         "recipient": "alpha_3", "text": "second"},
        {"sequence": 5, "event_type": "resident_action", "event_number": 4, "principal_id": "alpha_1",
         "action_type": "send_message", "success": True},
    ]
    text = [r["description"] for r in _resident_action_rows(events, {})]
    assert text == ["messaged alpha_2: “first”",
                    "tried to send message — refused by the kernel (empty_message)",
                    "messaged alpha_3: “second”"]


def test_transfer_shows_amount_and_recipient_in_feed_and_matrix(tmp_path: Path) -> None:
    world, kernel, client = _kernel(tmp_path)
    for amount in (7, 3):
        out = _act(client, kernel, "alpha_1", {"action_type": "transfer", "recipient_id": "alpha_2",
                                              "amount": amount, "memo": "for the gcd helper"})
        assert out["success"] is True, out
    events = _events(world)
    assert [(e["sender"], e["recipient"], e["amount"]) for e in events if e.get("event_type") == "transfer"] == [
        ("alpha_1", "alpha_2", 7), ("alpha_1", "alpha_2", 3)]
    rows = [r for r in _resident_action_rows(events, {}) if r["action"] == "transfer"]
    assert [r["description"] for r in rows] == [
        "paid alpha_2 7 scrip: “for the gcd helper”", "paid alpha_2 3 scrip: “for the gcd helper”"]
    assert [(r["value_amount"], r["value_unit"], r["counterparty"]) for r in rows] == [
        (7, "scrip", "alpha_2"), (3, "scrip", "alpha_2")]

    state = world.get_state_summary(event_limit=0)
    out = _agent_graph(events, state)
    edges = {e["id"]: e for e in out["graph"]["edges"]}
    assert set(edges) == {"paid:alpha_1->alpha_2"}
    assert edges["paid:alpha_1->alpha_2"]["label"] == "paid scrip ×10"
    assert out["details"]["paid:alpha_1->alpha_2"] == "Agent 1 paid Agent 2 10 scrip in 2 transfers."
    assert out["summary"]["transfers"] == 2 and out["summary"]["scrip_transferred"] == 10


def test_bought_code_is_its_own_matrix_relation(tmp_path: Path) -> None:
    world, kernel, client = _kernel(tmp_path)
    assert _act(client, kernel, "alpha_1", {"action_type": "write_artifact", "artifact_id": "alpha_1_gcd",
                                           "artifact_type": "solution:demo/gcd", "content": "x",
                                           "read_price": 4})["success"] is True
    assert _act(client, kernel, "alpha_2", {"action_type": "read_artifact", "artifact_id": "alpha_1_gcd"})["success"]
    events = _events(world)
    out = _agent_graph(events, world.get_state_summary(event_limit=0))
    assert {e["id"]: e["label"] for e in out["graph"]["edges"]} == {"bought:alpha_2->alpha_1": "bought code ×1"}
    assert out["details"]["bought:alpha_2->alpha_1"] == "Agent 2 bought Agent 1's code 1 time, paying 4 scrip."
    rows = _resident_action_rows(events, {"alpha_1_gcd": "alpha_1"})
    assert rows[-1]["description"] == "bought alpha_1_gcd from alpha_1" and rows[-1]["value_amount"] == 4


def test_live_feed_counts_every_event_of_a_run_longer_than_2000(tmp_path: Path) -> None:
    """The live /operator-state read the last 2,000 events while the other views read 100,000."""
    world, kernel, _ = _kernel(tmp_path, actions_per_turn=10_000)
    agent = kernel.agents["alpha_1"]

    async def many() -> None:
        for n in range(800):
            await kernel.act(agent, {"action_type": "write_artifact", "artifact_id": f"alpha_1_n{n}",
                                     "artifact_type": "note", "content": "x"})

    asyncio.run(many())
    events = _events(world)
    resident = [e for e in events if e.get("event_type") == "resident_action"]
    assert len(events) > 2000 and len(resident) == 800
    first_logged = resident[0]
    app = create_app(world_provider=lambda: world, runner_provider=lambda: None,
                     recovery_provider=lambda: {}, shutdown_provider=lambda: None)
    with TestClient(app) as client:
        state = client.get("/operator-state").json()
    assert len(state["actions"]) == 800
    assert state["actions"][0]["event_number"] == first_logged["event_number"]
    by_id = {a["id"]: a for a in state["agents"]}
    assert sum(by_id["alpha_1"]["action_counts"].values()) == 800
