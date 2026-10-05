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
    assert [e["rule_id"] for e in bundle["events"]] == [RULE_PAID_READ, RULE_SOLVED, RULE_UNPAID]
    world = _replay(bundle)
    members = {p: world["entities"][p]["components"]["member"] for p in ("alpha_1", "alpha_2")}
    assert members["alpha_1"] == {"scrip": 108, "solved": 1, "bought": 1, "sold": 0}
    assert members["alpha_2"]["scrip"] == 102 and members["alpha_2"]["sold"] == 1
    task = world["entities"]["task-HumanEval-34"]["components"]["resource"]
    assert task["current"] == 1 and task["solver"] == "alpha_1"
    assert bundle["projection_final_hash"] == _material_hash(world)


def test_profile_is_living_scene_v1_with_truthful_label() -> None:
    bundle = build_projection(EVENTS, run_id="t", principals=["alpha_1", "alpha_2"],
                              task_ids=["HumanEval/34"], starting_scrip=100)
    profile = build_profile(bundle, principals=["alpha_1", "alpha_2"], task_ids=["HumanEval/34"])
    assert profile["schema_version"] == "world-substrate-living-scene/v1"
    assert profile["world"] == bundle["world_id"]
    assert profile["note"] == LABEL
    assert set(profile["event_visuals"]) == {"ae3.market.paid_read", "ae3.market.transfer", "ae3.mint.task_solved", "ae3.mint.submission_unpaid"}


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
