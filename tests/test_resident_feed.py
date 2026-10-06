"""Activity feed rows for resident-agent runs (Plan 26 M1); no model calls."""

from __future__ import annotations

from typing import Any

from agent_ecology3.dashboard.server import _operator_state, _resident_action_rows


def _events() -> list[dict[str, Any]]:
    e: list[dict[str, Any]] = [
        {"sequence": 1, "event_type": "artifact_read", "event_number": 1, "principal_id": "alpha_2",
         "artifact_id": "alpha_1_task_x", "read_price_paid": 2, "recipient": "alpha_1"},
        {"sequence": 2, "event_type": "resident_action", "event_number": 1, "turn": 1, "principal_id": "alpha_2",
         "action_type": "read_artifact", "artifact_id": "alpha_1_task_x", "success": True},
        {"sequence": 3, "event_type": "task_bounty_scored", "event_number": 2, "principal_id": "alpha_2",
         "artifact_id": "alpha_2_sol", "task_id": "CF/X/gsum", "passed": True, "first_claim": True,
         "scrip_minted": 10, "reason": "CF/X/gsum: passed all hidden tests"},
        {"sequence": 4, "event_type": "royalty_paid", "event_number": 2, "principal_id": "alpha_1",
         "solver": "alpha_2", "amount": 3},
        {"sequence": 5, "event_type": "resident_action", "event_number": 2, "turn": 1, "principal_id": "alpha_2",
         "action_type": "submit_to_mint", "artifact_id": "alpha_2_sol", "success": True},
        # Refused: shares event number 2 but must not take alpha_2's result.
        {"sequence": 6, "event_type": "resident_action", "event_number": 2, "turn": 1, "principal_id": "alpha_1",
         "action_type": "submit_to_mint", "artifact_id": "alpha_1_sol", "success": False,
         "error_code": "turn_action_limit"},
        {"sequence": 7, "event_type": "task_bounty_scored", "event_number": 3, "principal_id": "alpha_1",
         "artifact_id": "alpha_1_sol", "task_id": "CF/X/digits", "passed": False, "first_claim": False,
         "reason": "CF/X/digits: failed hidden tests (AssertionError: ('(7,)', '7'))"},
        {"sequence": 8, "event_type": "resident_action", "event_number": 3, "turn": 2, "principal_id": "alpha_1",
         "action_type": "submit_to_mint", "artifact_id": "alpha_1_sol", "success": True},
        {"sequence": 9, "event_type": "resident_turn", "turn": 2, "principal_id": "alpha_1", "note": "will retry"},
    ]
    return e


def test_resident_rows_describe_trades_submissions_royalties_and_refusals() -> None:
    rows = _resident_action_rows(_events(), {"alpha_1_task_x": "alpha_1"})
    text = [r["description"] for r in rows]
    assert text[0] == "bought alpha_1_task_x from alpha_1" and rows[0]["value_amount"] == 2
    assert text[1] == "submitted CF/X/gsum: passed the hidden tests; reused helpers, royalty to alpha_1 (3 scrip)"
    assert rows[1]["value_amount"] == 10 and rows[1]["success"] is True
    assert text[2] == "tried to submit alpha_1_sol — refused by the kernel (turn_action_limit)"
    assert rows[2]["success"] is False and rows[2]["value_amount"] == 0
    assert text[3] == "submitted CF/X/digits: failed the hidden tests (AssertionError)"
    assert "('(7,)'" not in text[3]  # the hidden test case itself is not shown
    assert text[4] == "ended turn 2: will retry" and [r["turn"] for r in rows] == [1, 2, 3, 4, 5]


def test_operator_state_uses_resident_rows_and_drops_budget() -> None:
    world_state = {"run_id": "r", "principals": ["alpha_1", "alpha_2"], "artifacts": [],
                   "balances": {"alpha_1": {"scrip": 103, "resources": {"llm_budget": 1.0}}}}
    state = _operator_state(condition="live", world_state=world_state, recovery={}, model=None,
                            events=_events(), read_only=True)
    assert state["run_kind"] == "resident" and state["max_turn"] == 5
    by_id = {a["id"]: a for a in state["agents"]}
    assert by_id["alpha_1"]["llm_budget"] is None and by_id["alpha_2"]["tasks_solved"] == 1
