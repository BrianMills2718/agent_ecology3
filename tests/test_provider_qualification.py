from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agent_ecology3.analysis.provider_qualification import (
    EVALUATION_05,
    EVALUATION_06,
    _build_cases,
    _fixed_state,
    _run_public_readback_control_isolated,
    _summarize,
    classify_attempt,
    run_live,
)


@pytest.fixture(scope="module")
def public_readback_control() -> dict[str, object]:
    return _run_public_readback_control_isolated(Path.cwd())


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
            "response": "",
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
            "response": "",
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
        call_record={
            "content_persistence": "full",
            "response": "prose only",
            "response_tool_calls": [],
        },
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
            "response": "",
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
        call_record={
            "content_persistence": "full",
            "response": "",
            "response_tool_calls": [],
        },
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
            "response": None,
            "response_tool_calls": None,
        },
    )

    assert result["terminal_class"] == "custody_failure"
    assert result["usable"] is False


def test_nonidentical_retained_response_fails_custody() -> None:
    result = classify_attempt(
        principal_id="alpha_1",
        syscall_result={
            "success": True,
            "trace_id": "ae3/eval05/event_8/payer/alpha_1",
            "content": '{"action_type":"query_kernel","query_type":"resources"}',
            "tool_calls": [],
        },
        receipt={"status": "succeeded", "finish_reason": "stop"},
        call_record={
            "response": '{"action_type":"query_kernel","query_type":"events"}',
            "response_tool_calls": [],
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


def test_public_readback_control_accepts_exact_full_record(
    public_readback_control: dict[str, object],
) -> None:
    records = public_readback_control["records"]
    assert isinstance(records, dict)
    positive = records["positive"]

    assert public_readback_control["provider_calls"] == 0
    assert public_readback_control["zero_cost"] is True
    assert public_readback_control["public_positive_record_has_content_persistence"] is False
    assert positive["classification"]["terminal_class"] == "usable_tool_action"
    assert positive["call_record"]["response"] == ""
    assert len(positive["call_record"]["response_tool_calls"]) == 1


def test_public_readback_control_rejects_metadata_only_record(
    public_readback_control: dict[str, object],
) -> None:
    records = public_readback_control["records"]
    assert isinstance(records, dict)
    redaction = records["redaction"]

    assert redaction["call_record"]["response"] is None
    assert redaction["call_record"]["response_tool_calls"] is None
    assert redaction["classification"]["terminal_class"] == "custody_failure"


def test_public_readback_control_rejects_corrupted_record(
    public_readback_control: dict[str, object],
) -> None:
    records = public_readback_control["records"]
    assert isinstance(records, dict)
    corruption = records["corruption"]

    assert corruption["call_record"]["response_tool_calls"] == []
    assert corruption["classification"]["terminal_class"] == "custody_failure"
    assert public_readback_control["passed"] is True


def test_evaluation_06_uses_held_out_inputs_and_output() -> None:
    repo = Path.cwd()

    assert EVALUATION_06.evaluation_id == 6
    assert EVALUATION_06.state_path != EVALUATION_05.state_path
    assert EVALUATION_06.output_path != EVALUATION_05.output_path
    assert EVALUATION_06.preregistration_path != EVALUATION_05.preregistration_path
    assert (repo / EVALUATION_06.state_path).read_bytes() != (
        repo / EVALUATION_05.state_path
    ).read_bytes()
    assert _fixed_state(repo, "alpha_1", EVALUATION_06)["memory"]["turn"] == 7


def test_live_runner_stops_before_dispatch_when_public_control_fails(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "agent_ecology3.analysis.provider_qualification._verify_frozen_inputs",
        lambda _repo, _spec: {},
    )
    monkeypatch.setattr(
        "agent_ecology3.analysis.provider_qualification._git_revision_and_cleanliness",
        lambda _repo: ("test-revision", True),
    )
    monkeypatch.setattr(
        "agent_ecology3.analysis.provider_qualification._run_local_controls",
        lambda _repo: {"returncode": 0},
    )
    monkeypatch.setattr(
        "agent_ecology3.analysis.provider_qualification._verify_shared_custody_schema",
        lambda: None,
    )

    with pytest.raises(RuntimeError, match="controls failed before provider dispatch"):
        asyncio.run(
            run_live(
                Path.cwd(),
                tmp_path / "evidence",
                EVALUATION_06,
                public_control={"passed": False, "provider_calls": 0},
            )
        )

    evidence = tmp_path / "evidence"
    assert evidence.is_dir()
    inventory = json.loads((evidence / "run_inventory.json").read_text())
    assert inventory["completed_attempts"] == 0
    assert inventory["summary"]["verdict"] == "invalid_assay"
    assert inventory["summary"]["actual_cost_usd"] == 0.0
    assert (evidence / "SHA256SUMS").is_file()
