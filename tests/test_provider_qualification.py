from __future__ import annotations

from agent_ecology3.analysis.provider_qualification import (
    _build_cases,
    _summarize,
    classify_attempt,
)


def _valid_tool_call() -> dict[str, object]:
    return {
        "id": "call-1",
        "type": "function",
        "function": {
            "name": "ae3_action",
            "arguments": '{"action_type":"query_kernel","query_type":"resources","params":{}}',
        },
    }


def test_valid_tool_call_and_exact_custody_pass() -> None:
    tool_call = _valid_tool_call()
    result = classify_attempt(
        principal_id="alpha_1",
        syscall_result={
            "success": True,
            "trace_id": "ae3/eval05/event_1/payer/alpha_1",
            "content": "",
            "tool_calls": [tool_call],
        },
        receipt={"status": "succeeded", "finish_reason": "tool_calls"},
        call_record={
            "content_persistence": "full",
            "response_tool_calls": [tool_call],
        },
    )

    assert result["terminal_class"] == "usable_tool_action"
    assert result["usable"] is True
    assert result["action"]["action_type"] == "query_kernel"


def test_malformed_or_missing_tool_call_fails() -> None:
    malformed = _valid_tool_call()
    malformed["function"] = {"name": "ae3_action", "arguments": "not json"}

    malformed_result = classify_attempt(
        principal_id="alpha_1",
        syscall_result={
            "success": True,
            "trace_id": "ae3/eval05/event_2/payer/alpha_1",
            "content": "",
            "tool_calls": [malformed],
        },
        receipt={"status": "succeeded", "finish_reason": "tool_calls"},
        call_record={
            "content_persistence": "full",
            "response_tool_calls": [malformed],
        },
    )
    missing_result = classify_attempt(
        principal_id="alpha_1",
        syscall_result={
            "success": True,
            "trace_id": "ae3/eval05/event_3/payer/alpha_1",
            "content": "prose only",
            "tool_calls": [],
        },
        receipt={"status": "succeeded", "finish_reason": "stop"},
        call_record={"content_persistence": "full", "response_tool_calls": []},
    )

    assert malformed_result["terminal_class"] == "missing_or_malformed_action"
    assert malformed_result["usable"] is False
    assert missing_result["terminal_class"] == "missing_or_malformed_action"
    assert missing_result["usable"] is False


def test_illegal_action_fails() -> None:
    tool_call = _valid_tool_call()
    tool_call["function"] = {
        "name": "ae3_action",
        "arguments": '{"action_type":"destroy_world"}',
    }
    result = classify_attempt(
        principal_id="alpha_1",
        syscall_result={
            "success": True,
            "trace_id": "ae3/eval05/event_4/payer/alpha_1",
            "content": "",
            "tool_calls": [tool_call],
        },
        receipt={"status": "succeeded", "finish_reason": "tool_calls"},
        call_record={
            "content_persistence": "full",
            "response_tool_calls": [tool_call],
        },
    )

    assert result["terminal_class"] == "illegal_action"
    assert result["usable"] is False


def test_truncation_and_custody_mismatch_fail() -> None:
    tool_call = _valid_tool_call()
    truncation = classify_attempt(
        principal_id="alpha_1",
        syscall_result={
            "success": False,
            "trace_id": "ae3/eval05/event_5/payer/alpha_1",
            "error": "provider stopped at maximum output tokens",
        },
        receipt={"status": "failed", "finish_reason": "length"},
        call_record={"content_persistence": "full", "response_tool_calls": None},
    )
    mismatch = classify_attempt(
        principal_id="alpha_1",
        syscall_result={
            "success": True,
            "trace_id": "ae3/eval05/event_6/payer/alpha_1",
            "content": "",
            "tool_calls": [tool_call],
        },
        receipt={"status": "succeeded", "finish_reason": "tool_calls"},
        call_record={"content_persistence": "full", "response_tool_calls": []},
    )

    assert truncation["terminal_class"] == "output_truncation"
    assert mismatch["terminal_class"] == "custody_failure"


def test_metadata_only_call_record_fails_custody() -> None:
    tool_call = _valid_tool_call()
    result = classify_attempt(
        principal_id="alpha_1",
        syscall_result={
            "success": True,
            "trace_id": "ae3/eval05/event_7/payer/alpha_1",
            "content": "",
            "tool_calls": [tool_call],
        },
        receipt={"status": "succeeded", "finish_reason": "tool_calls"},
        call_record={
            "content_persistence": "metadata_only",
            "response_tool_calls": None,
        },
    )

    assert result["terminal_class"] == "custody_failure"
    assert result["usable"] is False


def test_missing_trace_fails() -> None:
    result = classify_attempt(
        principal_id="alpha_1",
        syscall_result={"success": True, "content": "{}", "tool_calls": []},
        receipt=None,
        call_record=None,
    )

    assert result["terminal_class"] == "trace_failure"
    assert result["usable"] is False


def test_frozen_case_order_is_balanced_and_alternating() -> None:
    cases = _build_cases()

    assert len(cases) == 32
    assert [case["ordinal"] for case in cases] == list(range(1, 33))
    assert [case["condition"] for case in cases] == [
        condition
        for _ in range(16)
        for condition in ("prescribed", "minimal")
    ]
    for condition in ("prescribed", "minimal"):
        selected = [case for case in cases if case["condition"] == condition]
        assert len(selected) == 16
        assert {case["round"] for case in selected} == {1, 2, 3, 4}
        assert {case["principal_id"] for case in selected} == {
            "alpha_1",
            "alpha_2",
            "alpha_3",
            "alpha_4",
        }


def test_frozen_summary_requires_threshold_and_zero_hard_failures() -> None:
    records = []
    for condition in ("prescribed", "minimal"):
        for ordinal in range(16):
            records.append(
                {
                    "case": {"condition": condition},
                    "classification": {
                        "terminal_class": (
                            "missing_or_malformed_action"
                            if condition == "minimal" and ordinal == 15
                            else "usable_tool_action"
                        ),
                        "usable": not (condition == "minimal" and ordinal == 15),
                    },
                    "cost_usd": 0.001,
                }
            )

    qualified = _summarize(records)
    records[0]["classification"] = {
        "terminal_class": "provider_timeout",
        "usable": False,
    }
    hard_failure = _summarize(records)

    assert qualified["verdict"] == "qualified"
    assert qualified["conditions"]["minimal"]["usable"] == 15
    assert hard_failure["verdict"] == "not_qualified"
    assert hard_failure["conditions"]["prescribed"]["usable"] == 15
