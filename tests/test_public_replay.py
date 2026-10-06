"""Public replay snapshot (scripts/build_public_replay.py) leaks nothing private; no model calls."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _module() -> Any:
    spec = importlib.util.spec_from_file_location("build_public_replay", SCRIPTS / "build_public_replay.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STATEMENT = "Calculate the sum of the digits of a given integer x for the gcd step."
TEST_INPUT = "(123456,)"
CODE = "def digits(x):\n    return sum(int(c) for c in str(x))  # secret solution body\n"
TOKEN = "sk-or-v1-0123456789abcdef0123456789abcdef"
HOME = "/home/brian/.local/state/agent_ecology3/run_x/logs/run_x/events.jsonl"
BANK_ROWS = [
    {"task_id": "CF/X/digits", "entry_point": "digits", "requires": [],
     "prompt": "Write the Python function `digits`.\n\n" + STATEMENT,
     "test": '_CASES = [["' + TEST_INPUT + '", "21"]]\n'},
]


def _fixture(tmp_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, dict[str, Any]], Any]:
    module = _module()
    bank_path = tmp_path / "bank.jsonl"
    bank_path.write_text("".join(json.dumps(r) + "\n" for r in BANK_ROWS))
    events: list[dict[str, Any]] = [
        {"event_type": "world_initialized", "sequence": 1, "event_number": 0, "run_id": "run_x"},
        {"event_type": "artifact_read", "sequence": 2, "event_number": 1, "principal_id": "alpha_2",
         "artifact_id": "alpha_1_task_X_digits", "read_price_paid": 2, "recipient": "alpha_1", "content_size": 99},
        {"event_type": "action", "sequence": 3, "event_number": 1,
         "intent": {"content": CODE}, "result": {"data": STATEMENT}},
        {"event_type": "resident_action", "sequence": 4, "event_number": 1, "turn": 1, "principal_id": "alpha_2",
         "session_id": "01a10f9b-session", "action_type": "read_artifact", "artifact_id": "alpha_1_task_X_digits",
         "success": True, "error_code": None},
        {"event_type": "artifact_written", "sequence": 5, "event_number": 2, "principal_id": "alpha_2",
         "artifact_id": "alpha_2_solution_X_digits", "artifact_type": "solution:CF/X/digits", "was_update": False,
         "content": CODE},
        {"event_type": "resident_action", "sequence": 6, "event_number": 2, "turn": 1, "principal_id": "alpha_2",
         "action_type": "write_artifact", "artifact_id": "alpha_2_solution_X_digits", "success": True},
        {"event_type": "task_bounty_scored", "sequence": 7, "event_number": 3, "principal_id": "alpha_2",
         "artifact_id": "alpha_2_solution_X_digits", "task_id": "CF/X/digits", "passed": False, "first_claim": False,
         "scrip_minted": 0, "reason": f"CF/X/digits: failed hidden tests (AssertionError: {TEST_INPUT} -> 20, want 21)"},
        {"event_type": "resident_action", "sequence": 8, "event_number": 3, "turn": 1, "principal_id": "alpha_2",
         "action_type": "submit_to_mint", "artifact_id": "alpha_2_solution_X_digits", "success": True},
        {"event_type": "agent_message", "sequence": 9, "event_number": 3, "principal_id": "alpha_2",
         "recipient": "alpha_1", "action_id": 4, "text": f"The task says: {STATEMENT} Try {TEST_INPUT}."},
        {"event_type": "resident_action", "sequence": 10, "event_number": 3, "turn": 1, "principal_id": "alpha_2",
         "action_type": "send_message", "action_id": 4, "success": True},
        {"event_type": "transfer", "sequence": 11, "event_number": 4, "sender": "alpha_2", "recipient": "alpha_1",
         "amount": 3, "memo": f"thanks for {STATEMENT} mail me at someone@example.com"},
        {"event_type": "resident_action", "sequence": 12, "event_number": 4, "turn": 1, "principal_id": "alpha_2",
         "action_type": "transfer", "success": True},
        {"event_type": "resident_turn", "sequence": 13, "turn": 1, "principal_id": "alpha_2",
         "session_id": "01a10f9b-session", "trace_id": "ae3/run_x/turn_1/alpha_2",
         "note": f"I learned {STATEMENT} My code: {CODE} Key {TOKEN} in {HOME}"},
    ]
    world_state = {
        "run_id": "run_x", "principals": ["alpha_1", "alpha_2"], "log_path": HOME,
        "balances": {"alpha_1": {"scrip": 105, "resources": {"llm_budget": 1.0}},
                     "alpha_2": {"scrip": 95, "resources": {"llm_budget": 1.0}}},
        "artifacts": [
            {"id": "alpha_1_task_X_digits", "type": "task_statement", "owner": "alpha_1",
             "content": BANK_ROWS[0]["prompt"], "metadata": {"plan24_task_id": "CF/X/digits", "test": BANK_ROWS[0]["test"]}},
            {"id": "alpha_2_solution_X_digits", "type": "solution:CF/X/digits", "owner": "alpha_2", "content": CODE,
             "metadata": {}},
        ],
    }
    return events, world_state, module._EVIDENCE._bank(bank_path), module


def test_fixture_is_leaky_before_redaction(tmp_path: Path) -> None:
    """Positive control: the checker finds every class of leak in the raw fixture."""
    events, world_state, bank, module = _fixture(tmp_path)
    counts = module.leak_counts(json.dumps(events) + json.dumps(world_state), bank)
    assert counts["bank sentence"] >= 1
    assert counts["hidden test input"] >= 1
    assert counts["token"] >= 1
    assert counts["home path"] >= 1
    assert counts["email address"] >= 1


def test_snapshot_and_living_bundle_leak_nothing(tmp_path: Path) -> None:
    events, world_state, bank, module = _fixture(tmp_path)
    snapshot = module.build_snapshot(events, world_state, agents_meta={"alpha_2": {"turns": 1}})
    from agent_ecology3.dashboard.server import _living_view_inputs
    from agent_ecology3.viz.world_substrate_view import build_projection

    public = module.redact_events(events)
    principals, task_ids = _living_view_inputs(public, module.public_world_state(world_state))
    bundle = build_projection(public, run_id="run_x", principals=principals, task_ids=task_ids, starting_scrip=100)
    blob = json.dumps(snapshot) + json.dumps(bundle)
    assert module.leak_counts(blob, bank) == {
        "bank sentence": 0, "hidden test input": 0, "home path": 0, "codex folder": 0, "email address": 0, "token": 0,
    }
    for private in (STATEMENT, TEST_INPUT, "sum(int(c)", TOKEN, "/home/", "01a10f9b-session", "trace_id", "someone@", "secret solution"):
        assert private not in blob, private
    assert '"content"' not in json.dumps(snapshot)  # no artifact bodies at all
    # The structure survives: who did what, with scrip and the checker's error type.
    words = [row["description"] for row in snapshot["actions"]]
    assert "bought alpha_1_task_X_digits from alpha_1" in words
    assert "submitted CF/X/digits: failed the hidden tests (AssertionError)" in words
    assert "paid alpha_1 3 scrip" in words
    assert any(w.startswith("messaged alpha_1: “(text withheld)") for w in words)
    assert "ended turn 1 (note withheld)" in words
    assert snapshot["graph"]["summary"]["transfers"] == 1
    assert [a["final_scrip"] for a in snapshot["agents"]] == [105, 95]


def test_unexpected_free_text_in_an_allowed_field_is_dropped(tmp_path: Path) -> None:
    _, _, bank, module = _fixture(tmp_path)
    event = {"event_type": "resident_action", "principal_id": "alpha_1", "action_type": "read_artifact",
             "error_code": f"weird: {STATEMENT}", "artifact_id": "ok_id"}
    [kept] = module.redact_events([event])
    assert kept["error_code"] is None and kept["artifact_id"] == "ok_id"


def test_build_refuses_when_a_leak_would_be_published(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    events, world_state, _, module = _fixture(tmp_path)
    run = tmp_path / "run_x"
    (run / "logs" / "run_x").mkdir(parents=True)
    (run / "logs" / "run_x" / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    (run / "run_receipt.json").write_text(json.dumps({"world_state": world_state, "agents": {}}))
    template = tmp_path / "page.html"
    template.write_text(f"<p>{STATEMENT}</p>")
    monkeypatch.setattr(module, "PAGE_TEMPLATE", template)
    monkeypatch.setattr(module, "render_living", lambda *a, **k: "<html></html>")
    out = tmp_path / "out"
    assert module.build(run, tmp_path / "bank.jsonl", out) == 1
    assert not out.exists()
