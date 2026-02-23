from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_ecology3.analysis.phase1_compare import compare_suite_files


def _suite_payload(*, condition: str, means: dict[str, float], by_seed: dict[int, dict[str, float]]) -> dict[str, object]:
    return {
        "records": [
            {
                "condition": condition,
                "summary": {
                    "aggregate": {key: {"mean": value} for key, value in means.items()},
                    "run_records": [
                        {"seed": seed, "metrics": metrics} for seed, metrics in sorted(by_seed.items())
                    ],
                    "gate_result": {"passed": True},
                    "runs_included_in_aggregate": len(by_seed),
                },
            }
        ]
    }


def test_compare_suite_files_reports_aggregate_and_matched_seed_deltas(tmp_path: Path) -> None:
    baseline_suite_path = tmp_path / "baseline_suite.json"
    candidate_suite_path = tmp_path / "candidate_suite.json"

    baseline_payload = _suite_payload(
        condition="baseline",
        means={
            "llm_valid_decision_rate": 0.9,
            "forced_explore_rate": 0.1,
            "cross_paid_consumption_amount": 1.0,
            "reuse_weighted_artifact_value_total": 2.0,
            "cross_transfer_amount": 4.0,
        },
        by_seed={
            100: {"cross_paid_consumption_amount": 1.0, "llm_valid_decision_rate": 0.9},
            101: {"cross_paid_consumption_amount": 1.0, "llm_valid_decision_rate": 0.8},
        },
    )
    candidate_payload = _suite_payload(
        condition="baseline",
        means={
            "llm_valid_decision_rate": 0.8,
            "forced_explore_rate": 0.2,
            "cross_paid_consumption_amount": 2.0,
            "reuse_weighted_artifact_value_total": 4.0,
            "cross_transfer_amount": 3.0,
        },
        by_seed={
            100: {"cross_paid_consumption_amount": 3.0, "llm_valid_decision_rate": 0.8},
            101: {"cross_paid_consumption_amount": 1.0, "llm_valid_decision_rate": 0.7},
        },
    )

    baseline_suite_path.write_text(json.dumps(baseline_payload), encoding="utf-8")
    candidate_suite_path.write_text(json.dumps(candidate_payload), encoding="utf-8")

    payload = compare_suite_files(
        baseline_suite=baseline_suite_path,
        candidate_suite=candidate_suite_path,
        metrics=[
            "llm_valid_decision_rate",
            "forced_explore_rate",
            "cross_paid_consumption_amount",
            "reuse_weighted_artifact_value_total",
            "cross_transfer_amount",
        ],
        conditions=["baseline"],
    )

    aggregate = payload["aggregate_deltas"]["baseline"]
    assert aggregate["llm_valid_decision_rate"]["delta"] == pytest.approx(-0.1)
    assert aggregate["forced_explore_rate"]["delta"] == pytest.approx(0.1)
    assert aggregate["cross_paid_consumption_amount"]["delta"] == pytest.approx(1.0)

    matched = payload["matched_seed_deltas"]["baseline"]["cross_paid_consumption_amount"]
    assert matched["count"] == 2
    assert matched["mean_delta"] == 1.0
    assert matched["seed_deltas"] == [{"seed": 100, "delta": 2.0}, {"seed": 101, "delta": 0.0}]

    advisory = payload["advisory"]
    assert any("increases paid consumption" in item for item in advisory["strengths"])
    assert any("lowers llm_valid_decision_rate" in item for item in advisory["risks"])
    assert any("raises forced_explore_rate" in item for item in advisory["risks"])


def test_compare_suite_files_uses_default_condition_intersection(tmp_path: Path) -> None:
    baseline_suite_path = tmp_path / "baseline_suite.json"
    candidate_suite_path = tmp_path / "candidate_suite.json"

    baseline_suite_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "condition": "baseline",
                        "summary": {
                            "aggregate": {"llm_calls": {"mean": 10.0}},
                            "run_records": [{"seed": 1, "metrics": {"llm_calls": 10.0}}],
                            "gate_result": {"passed": True},
                            "runs_included_in_aggregate": 1,
                        },
                    },
                    {
                        "condition": "off",
                        "summary": {
                            "aggregate": {"llm_calls": {"mean": 8.0}},
                            "run_records": [{"seed": 1, "metrics": {"llm_calls": 8.0}}],
                            "gate_result": {"passed": True},
                            "runs_included_in_aggregate": 1,
                        },
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    candidate_suite_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "condition": "off",
                        "summary": {
                            "aggregate": {"llm_calls": {"mean": 9.0}},
                            "run_records": [{"seed": 1, "metrics": {"llm_calls": 9.0}}],
                            "gate_result": {"passed": True},
                            "runs_included_in_aggregate": 1,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = compare_suite_files(
        baseline_suite=baseline_suite_path,
        candidate_suite=candidate_suite_path,
        metrics=["llm_calls"],
    )

    assert payload["conditions"] == ["off"]
    assert payload["aggregate_deltas"]["off"]["llm_calls"]["delta"] == 1.0
