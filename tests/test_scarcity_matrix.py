from __future__ import annotations

import textwrap

import pytest

from agent_ecology3.analysis.scarcity_matrix import aggregate_metrics, evaluate_kpi_lock
from agent_ecology3.analysis.scarcity_matrix import _build_matrix_gate_signals as build_matrix_gate_signals
from agent_ecology3.analysis.scarcity_matrix import _build_config as build_matrix_config
from agent_ecology3.analysis.scarcity_matrix import (
    _evaluate_llm_engagement_validity as evaluate_llm_engagement_validity,
)
from agent_ecology3.analysis.scarcity_matrix import _format_run_completion as format_run_completion
from agent_ecology3.analysis.scarcity_matrix import (
    _resolve_llm_preflight_enabled as resolve_llm_preflight_enabled,
)
from agent_ecology3.analysis.scarcity_matrix import (
    _resolve_llm_validity_thresholds as resolve_llm_validity_thresholds,
)

model_override_acceptance = {
    "accepted_by": "brian",
    "reason": "Tests exercise explicit matrix-run model overrides; MiniMax-M3 remains the baseline/default model.",
}


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


def test_format_run_completion_includes_key_signals() -> None:
    summary = {
        "llm_calls": 16,
        "forced_explore_rate": 0.125,
        "cross_paid_consumption_amount": 2.5,
    }
    message = format_run_completion(index=3, runs=10, run_id="run_abc", summary=summary)
    assert "run=3/10" in message
    assert "ae3_run_id=run_abc" in message
    assert "llm_calls=16" in message
    assert "forced_explore_rate=0.1250" in message
    assert "cross_paid_consumption_amount=2.5000" in message


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
    assert result["checks"]["loop_action_entropy_bits_mean"]["passed"] is False
    assert result["checks"]["repeat_error_rate_max"]["passed"] is False


def test_build_matrix_gate_signals_includes_aggregate_stats() -> None:
    payload = {
        "runs": 5,
        "runs_included_in_aggregate": 4,
        "runs_excluded_from_aggregate": 1,
        "preflight": {"enabled": True, "success": True},
        "kpi_lock": {"passed": False},
        "aggregate": {
            "loop_action_entropy_bits": {"mean": 2.2, "stdev": 0.1, "min": 2.0, "max": 2.4},
            "cross_transfer_amount": {"mean": 3.5, "stdev": 0.3, "min": 3.0, "max": 4.0},
        },
    }
    signals = build_matrix_gate_signals(payload)
    assert signals["runs"] == 5.0
    assert signals["llm_preflight_success"] == 1.0
    assert signals["kpi_lock_passed"] == 0.0
    assert signals["loop_action_entropy_bits"] == 2.2
    assert signals["loop_action_entropy_bits_mean"] == 2.2
    assert signals["cross_transfer_amount_max"] == 4.0


def test_build_config_applies_model_override_and_allowed_list(tmp_path) -> None:
    cfg = tmp_path / "config.yaml"
    prompt_template = tmp_path / "loop_prompt.txt"
    prompt_template.write_text("Template for {principal_id}", encoding="utf-8")
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
              default_model: minimax/minimax-m3
              timeout_seconds: 30
              allowed_models:
                - minimax/minimax-m3
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
        loop_forced_explore_mode=None,
        loop_policy_seed=17,
        loop_prompt_template_path=str(prompt_template),
        model_override="claude-code/opus",
        subscription_estimated_cost_multiplier=2.5,
        loop_cognition_mode="minimal",
    )
    assert loaded.llm.default_model == "claude-code/opus"
    assert "claude-code/opus" in loaded.llm.allowed_models
    assert loaded.llm.loop_policy_seed == 17
    assert loaded.llm.loop_prompt_template_path == str(prompt_template)
    assert loaded.llm.subscription_estimated_cost_multiplier == pytest.approx(2.5)
    assert loaded.llm.loop_cognition_mode == "minimal"


def test_build_config_rejects_negative_subscription_multiplier(tmp_path) -> None:
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
              default_model: minimax/minimax-m3
              timeout_seconds: 30
              allowed_models:
                - minimax/minimax-m3
              estimate_tokens_per_call: 500
              subscription_estimated_cost_multiplier: 1.0
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
    with pytest.raises(ValueError, match="--subscription-estimated-cost-multiplier must be >= 0"):
        build_matrix_config(
            config_path=str(cfg),
            agents=2,
            llm_loop=True,
            loop_llm_cooldown=0.0,
            loop_forced_explore_mode=None,
            loop_policy_seed=17,
            loop_prompt_template_path=None,
            model_override=None,
            subscription_estimated_cost_multiplier=-0.5,
        )


def test_resolve_llm_preflight_enabled_modes() -> None:
    assert (
        resolve_llm_preflight_enabled(
            mode="on",
            llm_loop_enabled=False,
            target_llm_calls=0,
            min_llm_calls=0,
        )
        is True
    )
    assert (
        resolve_llm_preflight_enabled(
            mode="off",
            llm_loop_enabled=True,
            target_llm_calls=100,
            min_llm_calls=1,
        )
        is False
    )
    assert (
        resolve_llm_preflight_enabled(
            mode="auto",
            llm_loop_enabled=True,
            target_llm_calls=100,
            min_llm_calls=0,
        )
        is True
    )
    assert (
        resolve_llm_preflight_enabled(
            mode="auto",
            llm_loop_enabled=False,
            target_llm_calls=100,
            min_llm_calls=0,
        )
        is False
    )
    with pytest.raises(ValueError, match="--llm-preflight must be one of: auto, on, off"):
        resolve_llm_preflight_enabled(
            mode="invalid",
            llm_loop_enabled=True,
            target_llm_calls=1,
            min_llm_calls=0,
        )


def test_resolve_llm_validity_thresholds_auto_applies_min_calls() -> None:
    thresholds = resolve_llm_validity_thresholds(
        llm_loop_enabled=True,
        target_llm_calls=80,
        min_llm_calls=None,
        min_llm_valid_decisions=None,
        min_llm_attempt_rate=None,
        min_llm_valid_decision_rate=None,
    )
    assert thresholds["min_llm_calls"] == 1
    assert thresholds["min_llm_valid_decisions"] == 0
    assert thresholds["min_llm_attempt_rate"] == 0.0
    assert thresholds["min_llm_valid_decision_rate"] == 0.0


def test_resolve_llm_validity_thresholds_rejects_invalid_ranges() -> None:
    with pytest.raises(ValueError, match="--min-llm-calls must be >= 0"):
        resolve_llm_validity_thresholds(
            llm_loop_enabled=True,
            target_llm_calls=10,
            min_llm_calls=-1,
            min_llm_valid_decisions=0,
            min_llm_attempt_rate=0.0,
            min_llm_valid_decision_rate=0.0,
        )
    with pytest.raises(ValueError, match="--min-llm-attempt-rate must be within \\[0, 1\\]"):
        resolve_llm_validity_thresholds(
            llm_loop_enabled=True,
            target_llm_calls=10,
            min_llm_calls=1,
            min_llm_valid_decisions=0,
            min_llm_attempt_rate=1.5,
            min_llm_valid_decision_rate=0.0,
        )
    with pytest.raises(ValueError, match="--min-llm-valid-decision-rate must be within \\[0, 1\\]"):
        resolve_llm_validity_thresholds(
            llm_loop_enabled=True,
            target_llm_calls=10,
            min_llm_calls=1,
            min_llm_valid_decisions=0,
            min_llm_attempt_rate=0.5,
            min_llm_valid_decision_rate=-0.1,
        )


def test_evaluate_llm_engagement_validity_reports_failed_checks() -> None:
    thresholds = {
        "min_llm_calls": 1,
        "min_llm_valid_decisions": 2,
        "min_llm_attempt_rate": 0.4,
        "min_llm_valid_decision_rate": 0.2,
    }
    summary = {
        "llm_calls": 0,
        "llm_valid_decision_total": 1,
        "llm_attempt_rate": 0.6,
        "llm_valid_decision_rate": 0.1,
    }
    result = evaluate_llm_engagement_validity(
        summary,
        {"llm_calls_observed": 0},
        thresholds=thresholds,
    )
    assert result["valid"] is False
    assert "min_llm_calls" in result["failed_checks"]
    assert "min_llm_valid_decisions" in result["failed_checks"]
    assert "min_llm_valid_decision_rate" in result["failed_checks"]
    assert result["checks"]["min_llm_attempt_rate"]["passed"] is True
