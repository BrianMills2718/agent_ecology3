from __future__ import annotations

import json

from agent_ecology3.analysis.emergence_report import summarize_events


def test_loop_decision_metrics_and_trends(tmp_path) -> None:
    events_path = tmp_path / "events.jsonl"
    events = [
        {
            "timestamp": "2026-02-21T00:00:00+00:00",
            "event_type": "llm_syscall",
            "payer_id": "alpha_1",
            "model": "test-model",
            "charged_cost": 0.01,
        },
        {
            "timestamp": "2026-02-21T00:00:00+00:00",
            "event_type": "llm_syscall_error",
            "payer_id": "alpha_1",
            "model": "test-model",
            "error": "boom",
        },
        {
            "timestamp": "2026-02-21T00:00:00.500000+00:00",
            "event_type": "artifact_written",
            "principal_id": "alpha_1",
            "artifact_id": "alpha_1_tool_a",
            "artifact_type": "tool",
        },
        {
            "timestamp": "2026-02-21T00:00:01+00:00",
            "event_type": "loop_decision",
            "principal_id": "alpha_1",
            "decision_action": "write_artifact",
            "decision": {
                "action_type": "write_artifact",
                "artifact_id": "alpha_1_tool_a",
            },
            "decision_origin": "llm_valid",
            "llm_attempted": True,
            "llm_success": True,
            "fallback_used": False,
            "result_success": True,
            "result_error_code": None,
        },
        {
            "timestamp": "2026-02-21T00:00:02+00:00",
            "event_type": "loop_decision",
            "principal_id": "alpha_1",
            "decision_action": "read_artifact",
            "decision_origin": "llm_invalid_fallback",
            "llm_attempted": True,
            "llm_success": False,
            "fallback_used": True,
            "result_success": False,
            "result_error_code": "not_authorized",
        },
        {
            "timestamp": "2026-02-21T00:00:03+00:00",
            "event_type": "loop_decision",
            "principal_id": "alpha_1",
            "decision_action": "read_artifact",
            "decision_origin": "llm_valid",
            "llm_attempted": True,
            "llm_success": True,
            "fallback_used": False,
            "result_success": False,
            "result_error_code": "not_authorized",
        },
        {
            "timestamp": "2026-02-21T00:00:04+00:00",
            "event_type": "loop_decision",
            "principal_id": "alpha_2",
            "decision_action": "submit_to_mint",
            "decision_origin": "forced_explore",
            "fallback_used": True,
            "forced_explore": True,
            "forced_explore_reason": "query_kernel_repeated",
            "result_success": False,
            "result_error_code": "invalid_action",
        },
        {
            "timestamp": "2026-02-21T00:00:04+00:00",
            "event_type": "artifact_read",
            "principal_id": "alpha_2",
            "artifact_id": "alpha_1_tool_a",
            "read_price_paid": 2,
            "recipient": "alpha_1",
        },
        {
            "timestamp": "2026-02-21T00:00:04+00:00",
            "event_type": "mint_auction",
            "winner_id": "alpha_1",
            "artifact_id": "alpha_1_tool_a",
            "price_paid": 1,
        },
        {
            "timestamp": "2026-02-21T00:00:05+00:00",
            "event_type": "resource_transfer",
            "sender": "alpha_1",
            "recipient": "alpha_2",
            "resource": "llm_budget",
            "amount": 0.4,
        },
    ]
    events_path.write_text("".join(json.dumps(item) + "\n" for item in events), encoding="utf-8")

    summary = summarize_events(events_path)

    assert summary["loop_decisions_total"] == 4
    assert summary["fallback_rate"] == 0.5
    assert summary["decision_success_rate"] == 0.25
    assert summary["repeat_error_rate"] == 0.3333
    assert summary["loop_action_entropy_bits"] == 1.5
    assert summary["loop_action_types"]["read_artifact"] == 2
    assert summary["resource_transfers_total"] == 1
    assert summary["llm_budget_transfer_amount"] == 0.4
    assert summary["cross_llm_budget_transfer_amount"] == 0.4
    assert summary["llm_calls"] == 1
    assert summary["llm_call_errors"] == 1
    assert summary["llm_attempted_total"] == 3
    assert summary["llm_success_total"] == 2
    assert summary["llm_valid_decision_total"] == 2
    assert summary["llm_attempt_rate"] == 0.75
    assert summary["llm_valid_decision_rate"] == 0.5
    assert summary["llm_attempt_success_rate"] == 0.6667
    assert summary["llm_error_rate"] == 0.5
    assert summary["forced_explore_rate"] == 0.25
    assert summary["decision_origin_counts"]["forced_explore"] == 1
    assert summary["cross_paid_consumption_amount"] == 2.0
    assert summary["cross_paid_consumption_events"] == 1
    assert summary["llm_valid_downstream_value"] == 2.0
    assert summary["specialization_hhi_mean"] == 1.0
    assert summary["minted_artifact_count"] == 1
    assert summary["minted_with_downstream_value_count"] == 1
    assert summary["mint_downstream_value"] == 2.0
    assert summary["mint_downstream_value_ratio"] == 1.0
    assert summary["value_by_decision_origin"]["llm_valid"] == 2.0
    assert summary["forced_explore_value_share"] == 0.0

    trends = summary["loop_decision_trends"]
    assert trends["alpha_1"]["decisions"] == 3
    assert trends["alpha_1"]["fallback_rate"] == 0.3333
    assert trends["alpha_1"]["decision_success_rate"] == 0.3333
    assert trends["alpha_1"]["repeat_error_rate"] == 0.5

    assert trends["alpha_2"]["decisions"] == 1
    assert trends["alpha_2"]["fallback_rate"] == 1.0
    assert trends["alpha_2"]["decision_success_rate"] == 0.0
    assert trends["alpha_2"]["repeat_error_rate"] == 0.0
