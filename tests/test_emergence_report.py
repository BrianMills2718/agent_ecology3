from __future__ import annotations

import json

from agent_ecology3.analysis.emergence_report import summarize_events


def test_loop_decision_metrics_and_trends(tmp_path) -> None:
    events_path = tmp_path / "events.jsonl"
    events = [
        {
            "timestamp": "2026-02-21T00:00:01+00:00",
            "event_type": "loop_decision",
            "principal_id": "alpha_1",
            "fallback_used": False,
            "result_success": True,
            "result_error_code": None,
        },
        {
            "timestamp": "2026-02-21T00:00:02+00:00",
            "event_type": "loop_decision",
            "principal_id": "alpha_1",
            "fallback_used": True,
            "result_success": False,
            "result_error_code": "not_authorized",
        },
        {
            "timestamp": "2026-02-21T00:00:03+00:00",
            "event_type": "loop_decision",
            "principal_id": "alpha_1",
            "fallback_used": False,
            "result_success": False,
            "result_error_code": "not_authorized",
        },
        {
            "timestamp": "2026-02-21T00:00:04+00:00",
            "event_type": "loop_decision",
            "principal_id": "alpha_2",
            "fallback_used": True,
            "result_success": False,
            "result_error_code": "invalid_action",
        },
    ]
    events_path.write_text("".join(json.dumps(item) + "\n" for item in events), encoding="utf-8")

    summary = summarize_events(events_path)

    assert summary["loop_decisions_total"] == 4
    assert summary["fallback_rate"] == 0.5
    assert summary["decision_success_rate"] == 0.25
    assert summary["repeat_error_rate"] == 0.3333

    trends = summary["loop_decision_trends"]
    assert trends["alpha_1"]["decisions"] == 3
    assert trends["alpha_1"]["fallback_rate"] == 0.3333
    assert trends["alpha_1"]["decision_success_rate"] == 0.3333
    assert trends["alpha_1"]["repeat_error_rate"] == 0.5

    assert trends["alpha_2"]["decisions"] == 1
    assert trends["alpha_2"]["fallback_rate"] == 1.0
    assert trends["alpha_2"]["decision_success_rate"] == 0.0
    assert trends["alpha_2"]["repeat_error_rate"] == 0.0
