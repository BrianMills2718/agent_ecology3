from __future__ import annotations

import json
from pathlib import Path

from agent_ecology3.analysis.matrix_progress import (
    _filter_aggregate_metrics as filter_aggregate_metrics,
)
from agent_ecology3.analysis.matrix_progress import load_progress_rows, summarize_progress


def test_load_progress_rows_parses_records_and_counts_malformed(tmp_path: Path) -> None:
    jsonl = tmp_path / "matrix.jsonl"
    jsonl.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "record": {
                            "ae3_run_id": "run_a",
                            "seed": 1000,
                            "replicate": 1,
                            "metrics": {
                                "llm_calls": 16.0,
                                "forced_explore_rate": 0.1,
                                "cross_paid_consumption_amount": 2.0,
                            },
                        }
                    }
                ),
                "{not-json",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows, malformed = load_progress_rows(jsonl)
    assert len(rows) == 1
    assert malformed == 1
    assert rows[0]["ae3_run_id"] == "run_a"


def test_summarize_progress_reports_last_run_and_aggregate() -> None:
    rows = [
        {
            "ae3_run_id": "run_a",
            "seed": 1000,
            "replicate": 1,
            "metrics": {
                "llm_calls": 16.0,
                "forced_explore_rate": 0.1,
                "cross_paid_consumption_amount": 2.0,
                "llm_valid_decision_rate": 0.8,
            },
        },
        {
            "ae3_run_id": "run_b",
            "seed": 1001,
            "replicate": 2,
            "metrics": {
                "llm_calls": 16.0,
                "forced_explore_rate": 0.05,
                "cross_paid_consumption_amount": 4.0,
                "llm_valid_decision_rate": 0.9,
            },
        },
    ]

    payload = summarize_progress(rows)
    assert payload["runs_completed"] == 2
    assert payload["last_run"]["ae3_run_id"] == "run_b"
    assert payload["last_run"]["seed"] == 1001
    assert payload["aggregate"]["cross_paid_consumption_amount"]["mean"] == 3.0


def test_filter_aggregate_metrics_respects_allow_list() -> None:
    aggregate = {
        "llm_calls": {"mean": 16.0},
        "forced_explore_rate": {"mean": 0.1},
    }
    filtered = filter_aggregate_metrics(aggregate, ["llm_calls"])
    assert filtered == {"llm_calls": {"mean": 16.0}}
