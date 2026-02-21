from __future__ import annotations

from agent_ecology3.analysis.scarcity_matrix import aggregate_metrics, evaluate_kpi_lock


def test_aggregate_metrics_computes_mean_stdev_min_max() -> None:
    rows = [
        {
            "metrics": {
                "action_entropy_bits": 2.1,
                "cross_transfer_amount": 4.0,
                "mint_submissions": 3.0,
                "decision_success_rate": 1.0,
                "repeat_error_rate": 0.0,
            }
        },
        {
            "metrics": {
                "action_entropy_bits": 2.2,
                "cross_transfer_amount": 3.0,
                "mint_submissions": 4.0,
                "decision_success_rate": 0.99,
                "repeat_error_rate": 0.0,
            }
        },
    ]

    aggregate = aggregate_metrics(rows)
    assert aggregate["action_entropy_bits"]["mean"] == 2.15
    assert aggregate["cross_transfer_amount"]["min"] == 3.0
    assert aggregate["cross_transfer_amount"]["max"] == 4.0
    assert aggregate["decision_success_rate"]["min"] == 0.99


def test_evaluate_kpi_lock_reports_pass_and_fail() -> None:
    passing = {
        "action_entropy_bits": {"mean": 2.14},
        "cross_transfer_amount": {"mean": 3.8},
        "mint_submissions": {"mean": 3.6},
        "decision_success_rate": {"min": 0.99},
        "repeat_error_rate": {"max": 0.0},
    }
    result = evaluate_kpi_lock(passing)
    assert result["passed"] is True
    assert all(item["passed"] for item in result["checks"].values())

    failing = {
        "action_entropy_bits": {"mean": 1.8},
        "cross_transfer_amount": {"mean": 1.0},
        "mint_submissions": {"mean": 1.0},
        "decision_success_rate": {"min": 0.9},
        "repeat_error_rate": {"max": 0.1},
    }
    result = evaluate_kpi_lock(failing)
    assert result["passed"] is False
    assert result["checks"]["action_entropy_bits_mean"]["passed"] is False
    assert result["checks"]["repeat_error_rate_max"]["passed"] is False
