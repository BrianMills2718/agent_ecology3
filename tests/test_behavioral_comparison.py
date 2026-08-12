from __future__ import annotations

import json
import shutil
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agent_ecology3.analysis.behavioral_comparison import (
    CASES_PATH,
    FROZEN_INPUT_SHA256,
    MAX_ACTUAL_COST_USD,
    _sha256,
    compute_readout,
    evaluate_run,
    finalize_interrupted_evidence,
    main,
    reproduce_evidence,
    run_live,
    run_preflight,
    verify_attempt_record,
    verify_frozen_inputs,
    write_manifest,
)
from agent_ecology3.analysis.emergence_report import summarize_events
from agent_ecology3.analysis.provider_qualification import _sha256_json


def _tool_call() -> dict[str, object]:
    return {
        "id": "call-1",
        "type": "function",
        "function": {
            "name": "ae3_action",
            "arguments": (
                '{"action_type":"query_kernel","query_type":"resources",'
                '"params":{}}'
            ),
        },
    }


def _attempt(ordinal: int, *, principal: str | None = None) -> dict[str, object]:
    principal_id = principal or f"alpha_{((ordinal - 1) % 4) + 1}"
    trace_id = f"ae3/eval07/test/{ordinal}/{principal_id}"
    action = {
        "action_type": "query_kernel",
        "query_type": "resources",
        "params": {},
    }
    tool = _tool_call()
    messages = [{"role": "user", "content": f"attempt {ordinal}"}]
    tools = [{"type": "function", "function": {"name": "ae3_action"}}]
    loop_decision = {
        "event_type": "loop_decision",
        "sequence": ordinal * 3,
        "principal_id": principal_id,
        "llm_trace_id": trace_id,
        "llm_attempted": True,
        "llm_success": True,
        "decision_origin": "llm_valid",
        "decision": action,
        "decision_action": "query_kernel",
        "fallback_used": False,
        "forced_explore": False,
        "result_success": True,
        "result_error_code": None,
    }
    return {
        "ordinal": ordinal,
        "condition": "prescribed",
        "pair_id": "pair_01",
        "principal_id": principal_id,
        "messages": messages,
        "messages_sha256": _sha256_json(messages),
        "tools": tools,
        "tools_sha256": _sha256_json(tools),
        "syscall_result": {
            "success": True,
            "trace_id": trace_id,
            "content": "",
            "tool_calls": [tool],
            "cache_hit": False,
        },
        "receipts": [
            {
                "trace_id": trace_id,
                "status": "succeeded",
                "finish_reason": "tool_calls",
                "retry_count": 0,
                "cache_hit": False,
                "cost_usd": 0.001,
            }
        ],
        "call_record": {
            "trace_id": trace_id,
            "messages": messages,
            "response": "",
            "response_tool_calls": [tool],
            "call_snapshot": {
                "request": {"kwargs": {"tools": tools}},
            },
        },
        "classification": {
            "terminal_class": "usable_tool_action",
            "usable": True,
            "action": action,
            "reason": None,
        },
        "loop_decision": loop_decision,
        "cost_usd": 0.001,
    }


def _valid_run(condition: str, pair_id: str, *, positive: bool) -> dict[str, object]:
    attempts = [_attempt(index) for index in range(1, 17)]
    for attempt in attempts:
        attempt["condition"] = condition
        attempt["pair_id"] = pair_id
    summary = {
        "llm_valid_decision_total": 16,
        "forced_explore_rate": 0.0,
        "llm_valid_downstream_value": 1.0 if positive else 0.0,
    }
    return evaluate_run(
        condition=condition,
        pair_id=pair_id,
        attempts=attempts,
        summary=summary,
        scarcity_receipts=[{"reason": "insufficient_funds"}],
        auxiliary_provider_calls=0,
    )


def _pairs(pattern: list[tuple[bool, bool]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index, (prescribed, minimal) in enumerate(pattern, start=1):
        pair_id = f"pair_{index:02d}"
        rows.append(
            {
                "pair_id": pair_id,
                "seed": 14000 + index,
                "valid": True,
                "runs": {
                    "prescribed": _valid_run("prescribed", pair_id, positive=prescribed),
                    "minimal": _valid_run("minimal", pair_id, positive=minimal),
                },
            }
        )
    return rows


def _write_reproduction_fixture(
    evidence: Path,
    *,
    pair_limit: int = 12,
) -> dict[str, object]:
    repo = Path.cwd()
    inputs = evidence / "inputs"
    inputs.mkdir(parents=True)
    for relative in FROZEN_INPUT_SHA256:
        shutil.copyfile(repo / relative, inputs / relative.replace("/", "__"))
    cases = json.loads((repo / CASES_PATH).read_text(encoding="utf-8"))
    dispatch = {
        "schema_version": "ae3_eval07_dispatch_plan_v1",
        "evaluation_id": 7,
        "implementation_revision": "fixture-revision",
        **{
            key: cases[key]
            for key in (
                "pair_schedule",
                "conditions",
                "execution",
                "run_validity",
                "readout",
            )
        },
    }
    attempts: list[dict[str, object]] = []
    pairs: list[dict[str, object]] = []
    ordinal = 1
    for spec in cases["pair_schedule"][:pair_limit]:
        pair_id = str(spec["pair_id"])
        seed = int(spec["seed"])
        first = str(spec["first_condition"])
        order = [first, "minimal" if first == "prescribed" else "prescribed"]
        runs: dict[str, object] = {}
        for condition in order:
            relative = f"runtime_logs/{condition}/{pair_id}/events.jsonl"
            events_path = evidence / relative
            events_path.parent.mkdir(parents=True)
            events: list[dict[str, object]] = []
            run_attempts: list[dict[str, object]] = []
            for run_ordinal in range(16):
                attempt = _attempt(ordinal)
                attempt.update(
                    {
                        "condition": condition,
                        "pair_id": pair_id,
                        "seed": seed,
                        "runtime_events_path": relative,
                    }
                )
                trace_id = str(attempt["syscall_result"]["trace_id"])
                loop = attempt["loop_decision"]
                loop["timestamp"] = "2026-08-12T00:00:01+00:00"
                if run_ordinal == 0:
                    loop["result_success"] = False
                    loop["result_error_code"] = "insufficient_funds"
                events.extend(
                    [
                        {
                            "timestamp": "2026-08-12T00:00:00+00:00",
                            "event_type": "llm_syscall",
                            "sequence": ordinal * 3 - 1,
                            "trace_id": trace_id,
                            "payer_id": attempt["principal_id"],
                            "actual_cost": 0.001,
                            "charged_cost": 0.001,
                            "cache_hit": False,
                            "tokens": {
                                "prompt_tokens": 10,
                                "completion_tokens": 5,
                                "total_tokens": 15,
                            },
                        },
                        loop,
                    ]
                )
                run_attempts.append(attempt)
                ordinal += 1
            events.append(
                {
                    "timestamp": "2026-08-12T00:00:02+00:00",
                    "event_type": "simulation_stopped",
                    "sequence": ordinal * 3,
                }
            )
            events_path.write_text(
                "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
                encoding="utf-8",
            )
            for attempt in run_attempts:
                attempt["verification"] = verify_attempt_record(
                    attempt,
                    runtime_events=events,
                )
            (events_path.parent / "attempts.checkpoint.json").write_text(
                json.dumps(run_attempts) + "\n",
                encoding="utf-8",
            )
            summary = summarize_events(events_path)
            scarcity = [
                {
                    "reason": "insufficient_funds",
                    "sequence": run_attempts[0]["loop_decision"]["sequence"],
                    "principal_id": run_attempts[0]["principal_id"],
                }
            ]
            run = evaluate_run(
                condition=condition,
                pair_id=pair_id,
                attempts=run_attempts,
                summary=summary,
                scarcity_receipts=scarcity,
                auxiliary_provider_calls=0,
                runtime_events=events,
            )
            run.update({"seed": seed, "events_path": relative, "elapsed_seconds": 1.0})
            runs[condition] = run
            attempts.extend(run_attempts)
        pairs.append(
            {
                "pair_id": pair_id,
                "seed": seed,
                "role": spec["role"],
                "condition_order": order,
                "valid": True,
                "included": True,
                "runs": runs,
            }
        )
    readout = compute_readout(pairs)
    cost = round(sum(float(attempt["cost_usd"]) for attempt in attempts), 8)
    values = {
        "controls.json": {"passed": True, "provider_calls": 0},
        "dispatch_plan.json": dispatch,
        "pairs.json": pairs,
        "attempts.json": attempts,
        "run_inventory.json": {
            "schema_version": "ae3_eval07_evidence_v1",
            "evaluation_id": 7,
            "git_revision": "fixture-revision",
            "completed_attempts": len(attempts),
            "completed_pairs": len(pairs),
            "valid_pairs": len(pairs),
            "actual_cost_usd": cost,
            "stop_reason": None,
            "readout_decision": readout["decision"],
        },
        "readout.json": readout,
    }
    for filename, value in values.items():
        (evidence / filename).write_text(json.dumps(value) + "\n", encoding="utf-8")
    write_manifest(evidence)
    return readout


def test_frozen_inputs_schedule_and_budget_pass() -> None:
    observed = verify_frozen_inputs(Path.cwd(), now=datetime(2026, 8, 12, tzinfo=UTC))

    assert observed["schedule"]["primary_pairs"] == 12
    assert observed["schedule"]["reserve_pairs"] == 2
    assert observed["schedule"]["balanced_first_condition"] is True
    assert observed["schedule"]["unique_seeds"] is True
    assert observed["schedule"]["maximum_provider_attempts"] == 448
    assert observed["schedule"]["maximum_actual_cost_usd"] == MAX_ACTUAL_COST_USD


def test_preflight_controls_are_zero_provider_and_detect_metric_origins() -> None:
    result = run_preflight(Path.cwd(), now=datetime(2026, 8, 12, tzinfo=UTC))

    assert result["passed"] is True
    assert result["provider_calls"] == 0
    assert result["public_readback"]["passed"] is True
    assert result["metric_controls"]["positive"]["llm_valid_downstream_value"] == 2.0
    assert result["metric_controls"]["negative"]["passed"] is True
    assert result["llm_off"]["runs"] == 3
    assert result["llm_off"]["provider_calls"] == 0
    assert result["corruption"]["passed"] is True


def test_attempt_record_verifier_rejects_normalized_action_corruption() -> None:
    attempt = _attempt(1)
    runtime_events = [deepcopy(attempt["loop_decision"])]

    verified = verify_attempt_record(attempt, runtime_events=runtime_events)
    assert verified["passed"] is True

    corrupted = deepcopy(attempt)
    corrupted["loop_decision"]["decision"]["action_type"] = "transfer"
    rejected = verify_attempt_record(corrupted, runtime_events=runtime_events)
    assert rejected["passed"] is False
    assert "runtime loop decision" in " ".join(rejected["errors"])


def test_run_validity_enforces_attempt_distribution_and_terminal_classes() -> None:
    attempts = [_attempt(index) for index in range(1, 17)]
    attempts[-1]["classification"] = {
        "terminal_class": "illegal_action",
        "usable": False,
        "action": {"action_type": "destroy_world"},
        "reason": "unknown action",
    }
    summary = {
        "llm_valid_decision_total": 15,
        "forced_explore_rate": 0.0,
        "llm_valid_downstream_value": 0.0,
    }

    result = evaluate_run(
        condition="prescribed",
        pair_id="pair_01",
        attempts=attempts,
        summary=summary,
        scarcity_receipts=[],
        auxiliary_provider_calls=0,
    )
    assert result["valid"] is True

    unbalanced = deepcopy(attempts)
    for attempt in unbalanced[:6]:
        attempt["principal_id"] = "alpha_1"
    invalid = evaluate_run(
        condition="prescribed",
        pair_id="pair_01",
        attempts=unbalanced,
        summary=summary,
        scarcity_receipts=[],
        auxiliary_provider_calls=0,
    )
    assert invalid["valid"] is False
    assert "attempt_distribution" in invalid["failed_checks"]


def test_readout_large_effect_robust_ambiguous_and_invalid() -> None:
    large = compute_readout(_pairs([(True, False)] * 8 + [(False, False)] * 4))
    robust = compute_readout(_pairs([(True, True)] * 9 + [(False, False)] * 3))
    ambiguous = compute_readout(
        _pairs([(True, True)] * 5 + [(True, False)] * 2 + [(False, False)] * 5)
    )
    invalid = compute_readout(_pairs([(True, True)] * 11), controls_passed=False)

    assert large["decision"] == "large_prescription_effect"
    assert large["exact_one_sided_p"] <= 0.05
    assert robust["decision"] == "prescription_robust_candidate"
    assert ambiguous["decision"] == "ambiguous_pilot"
    assert invalid["decision"] == "inconclusive_invalid"


def test_reproducer_verifies_manifest_and_saved_readout(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    readout = _write_reproduction_fixture(evidence)

    reproduced = reproduce_evidence(evidence)
    assert reproduced["passed"] is True
    assert reproduced["readout"] == readout

    (evidence / "readout.json").write_text(json.dumps({"decision": "tampered"}) + "\n")
    with pytest.raises(RuntimeError, match="manifest"):
        reproduce_evidence(evidence)

    (evidence / "readout.json").write_text(json.dumps(readout) + "\n")
    dispatch = json.loads((evidence / "dispatch_plan.json").read_text(encoding="utf-8"))
    dispatch["pair_schedule"][0]["seed"] = 99999
    (evidence / "dispatch_plan.json").write_text(json.dumps(dispatch) + "\n")
    write_manifest(evidence)
    with pytest.raises(RuntimeError, match="dispatch plan differs"):
        reproduce_evidence(evidence)


def test_interruption_finalizer_preserves_terminal_partial_bundle(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    _write_reproduction_fixture(evidence, pair_limit=1)
    raw_paths = sorted(
        path
        for path in evidence.rglob("*")
        if path.is_file()
        and (
            "runtime_logs" in path.parts
            or "inputs" in path.parts
            or path.name in {"controls.json", "dispatch_plan.json"}
        )
    )
    before = {str(path.relative_to(evidence)): _sha256(path) for path in raw_paths}
    for filename in (
        "attempts.json",
        "pairs.json",
        "readout.json",
        "run_inventory.json",
        "SHA256SUMS",
    ):
        (evidence / filename).unlink()

    inventory = finalize_interrupted_evidence(
        Path.cwd(),
        evidence,
        stop_reason="fixture process ended before pair 2",
        observed_at=datetime(2026, 8, 12, tzinfo=UTC),
    )

    after = {str(path.relative_to(evidence)): _sha256(path) for path in raw_paths}
    assert before == after
    assert inventory["settled_provider_attempts"] == 32
    assert inventory["completed_attempts"] == 32
    assert inventory["completed_pairs"] == 1
    assert inventory["valid_pairs"] == 1
    assert inventory["complete_reproduction_available"] is False
    assert inventory["readout_decision"] == "inconclusive_invalid"
    with pytest.raises(RuntimeError, match="terminal partial evidence"):
        reproduce_evidence(evidence)


def test_cli_refuses_live_dispatch_without_exact_cost_acknowledgement() -> None:
    with pytest.raises(SystemExit, match="choose exactly one"):
        main([])

    with pytest.raises(SystemExit, match="exact --acknowledge-max-cost-usd"):
        main(["--run-live", "--acknowledge-max-cost-usd", "1.67"])

    with pytest.raises(RuntimeError, match="exact USD 1.68 acknowledgement"):
        run_live(Path.cwd(), Path("unused-eval07-output"))
