from __future__ import annotations

import textwrap

from agent_ecology3.analysis.scarcity_matrix import aggregate_metrics, evaluate_kpi_lock
from agent_ecology3.analysis.scarcity_matrix import _build_config as build_matrix_config


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


def test_build_config_applies_model_override_and_allowed_list(tmp_path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        textwrap.dedent(
            """
            simulation:
              default_duration_seconds: 60
              max_runtime_seconds: 3600
              summary_interval_seconds: 10
              loop:
                min_delay_seconds: 0.1
                max_delay_seconds: 1.0
                max_consecutive_errors: 3
                resource_check_interval_seconds: 0.1
            principals:
              count: 2
              id_prefix: alpha_
              starting_scrip: 100
              starting_llm_budget: 2.0
              starting_disk_quota_bytes: 100000
            resources:
              rate_window_seconds: 60
              rate_limits:
                llm_calls_per_window: 10
                llm_tokens_per_window: 1000
                cpu_seconds_per_window: 5
              stock:
                total_llm_budget: 2.0
                total_disk_bytes: 1000000
            llm:
              default_model: gemini/gemini-2.5-flash
              timeout_seconds: 30
              allowed_models:
                - gemini/gemini-2.5-flash
              estimate_tokens_per_call: 500
              enable_bootstrap_loop_llm: false
            contracts:
              default_when_missing: kernel_contract_freeware
              default_for_new_artifact: kernel_contract_freeware
            mint:
              enabled: true
              minimum_bid: 1
              first_auction_delay_seconds: 20
              bidding_window_seconds: 30
              period_seconds: 60
              mint_ratio: 10
            dashboard:
              enabled: false
              host: 0.0.0.0
              port: 9000
              jsonl_file: logs/latest/events.jsonl
              poll_interval_seconds: 1.0
            logging:
              logs_dir: logs
              event_file_name: events.jsonl
              summary_file_name: summary.jsonl
              recent_event_limit: 100
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    loaded = build_matrix_config(
        config_path=str(cfg),
        agents=2,
        llm_loop=True,
        loop_llm_cooldown=0.0,
        model_override="claude-code/opus",
    )
    assert loaded.llm.default_model == "claude-code/opus"
    assert "claude-code/opus" in loaded.llm.allowed_models
