"""World Substrate living view adapter (viewer only)."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agent_ecology3.dashboard.server import create_app
from agent_ecology3.viz.world_substrate_view import (
    LABEL,
    RULE_PAID_READ,
    RULE_SOLVED,
    RULE_NOTE,
    RULE_UNPAID,
    WORLD_SUBSTRATE_REPO,
    _material_hash,
    _set,
    build_profile,
    build_projection,
)

EVENTS: list[dict[str, Any]] = [
    {"event_type": "artifact_read", "event_number": 1, "principal_id": "alpha_1", "recipient": "alpha_2", "read_price_paid": 2},
    {"event_type": "artifact_read", "event_number": 2, "principal_id": "alpha_2", "recipient": "alpha_2", "read_price_paid": 2},
    {"event_type": "task_bounty_scored", "event_number": 3, "principal_id": "alpha_1", "task_id": "HumanEval/34",
     "first_claim": True, "scrip_minted": 10, "passed": True},
    {"event_type": "task_bounty_scored", "event_number": 4, "principal_id": "alpha_2", "task_id": "HumanEval/34",
     "first_claim": False, "scrip_minted": 0, "passed": True},
]


def _replay(bundle: dict[str, Any]) -> dict[str, Any]:
    world = deepcopy(bundle["initial_snapshot"]["world"])
    for event in bundle["events"]:
        for change in event["changes"]:
            _set(world, change["path"], change["after"])
        assert _material_hash(world) == event["hash_after"]
    return world


def test_projection_replays_to_final_state_and_hash() -> None:
    bundle = build_projection(EVENTS, run_id="t", principals=["alpha_1", "alpha_2"],
                              task_ids=["HumanEval/34"], starting_scrip=100)
    assert bundle["schema_version"] == "world-substrate-live-projection/v0"
    assert [e["rule_id"] for e in bundle["events"]] == [
        f"{RULE_PAID_READ}.alpha_1", f"{RULE_SOLVED}.alpha_1", f"{RULE_UNPAID}.alpha_2"
    ]
    world = _replay(bundle)
    members = {p: world["entities"][p]["components"]["member"] for p in ("alpha_1", "alpha_2")}
    assert {k: members["alpha_1"][k] for k in ("scrip", "solved", "bought", "sold")} == {
        "scrip": 108, "solved": 1, "bought": 1, "sold": 0
    }
    assert members["alpha_2"]["scrip"] == 102 and members["alpha_2"]["sold"] == 1
    board = world["entities"]["task-board"]["components"]["resource"]
    assert board["current"] == 1 and board["last_solved"] == "HumanEval/34 by alpha_1"
    assert bundle["projection_final_hash"] == _material_hash(world)


def test_profile_is_living_scene_v1_with_truthful_label() -> None:
    bundle = build_projection(EVENTS, run_id="t", principals=["alpha_1", "alpha_2"],
                              task_ids=["HumanEval/34"], starting_scrip=100)
    profile = build_profile(bundle, principals=["alpha_1", "alpha_2"], task_ids=["HumanEval/34"])
    assert profile["schema_version"] == "world-substrate-living-scene/v1"
    assert profile["world"] == bundle["world_id"]
    assert profile["note"] == LABEL
    visuals = profile["event_visuals"]
    assert f"{RULE_PAID_READ}.alpha_1" in visuals and f"{RULE_NOTE}.alpha_2" in visuals
    moves = [op for op in visuals[f"{RULE_SOLVED}.alpha_1"]["operations"] if op["op"] == "actor.move_to"]
    assert moves == [{"op": "actor.move_to", "actor": "alpha_1", "entity": "checker", "animation_ms": 450}]


def test_resident_turn_note_becomes_public_message_at_the_workbench() -> None:
    events = [{"event_type": "resident_turn", "event_number": 9, "principal_id": "alpha_2", "turn": 1,
               "note": "Plan: solve task 34 next turn."}]
    bundle = build_projection(events, run_id="t", principals=["alpha_1", "alpha_2"],
                              task_ids=["HumanEval/34"], starting_scrip=100)
    world = _replay(bundle)
    info = world["entities"]["note-1"]["components"]["information"]
    delivery = world["entities"]["note-1-delivery"]["components"]["delivery"]
    assert info["visibility"] == "public" and info["active"] is True and info["source_id"] == "alpha_2"
    assert info["content"] == "Plan: solve task 34 next turn."
    assert delivery["recipient_id"] == "bench-alpha_2" and delivery["status"] == "delivered"


@pytest.mark.skipif(not (WORLD_SUBSTRATE_REPO / ".git").exists(), reason="world-substrate checkout not present")
def test_living_view_endpoint_renders_with_pinned_world_substrate(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    log_path.write_text("".join(json.dumps(e) + "\n" for e in EVENTS), encoding="utf-8")
    receipt = {
        "recovery": {"committed_attempts": 4, "target_attempts": 4, "lifecycle_state": "completed"},
        "world_state": {
            "principals": ["alpha_1", "alpha_2"],
            "balances": {"alpha_1": {"scrip": 108}, "alpha_2": {"scrip": 102}},
            "artifacts": [{"id": "alpha_2_task_34", "type": "task_statement"}],
            "log_path": str(log_path),
        },
    }
    (tmp_path / "run_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    with TestClient(create_app(review_runs={"run": tmp_path})) as client:
        page = client.get("/living-view?run=run")
        assert "Living view" in client.get("/").text
    assert page.status_code == 200
    assert LABEL in page.text and "id='scrub'" in page.text


def test_royalty_becomes_a_message_from_reuser_to_author() -> None:
    events = [{"event_type": "royalty_paid", "event_number": 5, "principal_id": "alpha_1",
               "solver": "alpha_2", "dependency_task_id": "CF/X/digits", "amount": 3}]
    bundle = build_projection(events, run_id="t", principals=["alpha_1", "alpha_2"],
                              task_ids=["CF/X/digits"], starting_scrip=100)
    world = _replay(bundle)
    info = world["entities"]["royalty-1"]["components"]["information"]
    assert info["source_id"] == "alpha_2" and info["content"] == "Agent 2 reused your digits: +3 scrip"
    assert world["entities"]["royalty-1-delivery"]["components"]["delivery"]["recipient_id"] == "alpha_1"
    assert world["entities"]["alpha_1"]["components"]["member"]["scrip"] == 103


def test_title_is_short_and_run_id_is_in_subtitle() -> None:
    """The renderer's tick badge covered long titles (plan25_codeflow_run2)."""
    bundle = build_projection(EVENTS, run_id="plan25_codeflow_run2", principals=["alpha_1"],
                              task_ids=["HumanEval/34"], starting_scrip=100)
    profile = build_profile(bundle, principals=["alpha_1"], task_ids=["HumanEval/34"])
    assert profile["title"] == "Agent Ecology 3"
    assert "plan25_codeflow_run2" in profile["subtitle"]


def test_sixteen_agents_are_in_number_order_with_named_benches() -> None:
    """plan25_codeflow_run3 showed Agent 1, 10, 11, ... 16, 2 and benches labelled "notes"."""
    principals = [f"alpha_{n}" for n in range(1, 17)]
    shuffled = sorted(principals)  # text order: alpha_1, alpha_10, ..., alpha_2
    bundle = build_projection(EVENTS, run_id="t", principals=shuffled, task_ids=["HumanEval/34"], starting_scrip=100)
    profile = build_profile(bundle, principals=shuffled, task_ids=["HumanEval/34"])
    actors = profile["actors"]
    xs = [actors[p]["home"][0] for p in principals]
    assert xs == sorted(xs) and len(set(xs)) == 16
    labels = [profile["entities"][f"bench-{p}"]["label"] for p in principals]
    assert labels[3] == "Bench 4"
    # No wider than the agent tag drawn over it ("Agent 16's bench" overran neighbours).
    assert all(len(b) <= len(actors[p]["label"]) for b, p in zip(labels, principals, strict=True))
