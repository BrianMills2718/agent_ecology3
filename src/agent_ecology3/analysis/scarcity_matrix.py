"""Run repeated scarcity-first simulations and aggregate emergence metrics."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Literal, cast

from ..config import AppConfig, load_config
from ..simulation import SimulationRunner
from ..world import World
from .emergence_report import _log_summary_to_llm_client, summarize_events


NUMERIC_METRICS: tuple[str, ...] = (
    "actions_total",
    "action_entropy_bits",
    "loop_action_entropy_bits",
    "cross_read_events",
    "cross_transfer_amount",
    "resource_transfers_total",
    "llm_budget_transfer_amount",
    "cross_llm_budget_transfer_amount",
    "mint_submissions",
    "llm_calls",
    "llm_call_errors",
    "llm_attempted_total",
    "llm_success_total",
    "llm_valid_decision_total",
    "llm_attempt_rate",
    "llm_valid_decision_rate",
    "llm_attempt_success_rate",
    "llm_error_rate",
    "llm_cost",
    "fallback_rate",
    "gate_fallback_rate",
    "recovery_fallback_rate",
    "forced_explore_rate",
    "decision_success_rate",
    "repeat_error_rate",
    "cross_paid_consumption_amount",
    "cross_paid_consumption_events",
    "reuse_weighted_artifact_value_total",
    "specialization_hhi_mean",
    "forced_explore_value_share",
    "minted_artifact_count",
    "minted_with_downstream_value_count",
    "mint_downstream_value",
    "mint_downstream_value_ratio",
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LLM_CLIENT_REPO = str(PROJECT_ROOT.parent / "llm_client")


def _load_experiment_eval_module() -> Any:
    """Load the llm_client experiment-eval module after optional path injection."""
    module: Any = importlib.import_module("llm_client.experiment_eval")
    return module


def aggregate_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    aggregate: dict[str, dict[str, float]] = {}
    if not rows:
        return aggregate
    for metric in NUMERIC_METRICS:
        values: list[float] = []
        for row in rows:
            metrics = row.get("metrics")
            if not isinstance(metrics, dict):
                continue
            value = metrics.get(metric)
            if isinstance(value, (int, float)):
                values.append(float(value))
        if not values:
            continue
        aggregate[metric] = {
            "mean": round(statistics.fmean(values), 6),
            "stdev": round(statistics.pstdev(values), 6),
            "min": round(min(values), 6),
            "max": round(max(values), 6),
        }
    return aggregate


def evaluate_kpi_lock(aggregate: dict[str, dict[str, float]]) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}

    entropy = aggregate.get("loop_action_entropy_bits")
    if not isinstance(entropy, dict):
        entropy = aggregate.get("action_entropy_bits", {})
    checks["loop_action_entropy_bits_mean"] = {
        "target": ">= 2.1",
        "observed": entropy.get("mean"),
        "passed": isinstance(entropy.get("mean"), float) and float(entropy["mean"]) >= 2.1,
    }

    cross_transfer = aggregate.get("cross_transfer_amount", {})
    cross_llm_budget_transfer = aggregate.get("cross_llm_budget_transfer_amount", {})
    resource_transfers_total = aggregate.get("resource_transfers_total", {})
    cross_transfer_mean = cross_transfer.get("mean")
    cross_llm_budget_transfer_mean = cross_llm_budget_transfer.get("mean")
    resource_transfers_total_mean = resource_transfers_total.get("mean")
    cross_exchange_passed = False
    if isinstance(cross_transfer_mean, float) and float(cross_transfer_mean) >= 3.0:
        cross_exchange_passed = True
    if isinstance(cross_llm_budget_transfer_mean, float) and float(cross_llm_budget_transfer_mean) >= 0.5:
        cross_exchange_passed = True
    if isinstance(resource_transfers_total_mean, float) and float(resource_transfers_total_mean) >= 2.0:
        cross_exchange_passed = True
    checks["cross_transfer_amount_mean"] = {
        "target": "scrip>=3.0 OR llm_budget>=0.5 OR resource_transfer_events>=2.0",
        "observed": {
            "scrip": cross_transfer_mean,
            "llm_budget": cross_llm_budget_transfer_mean,
            "resource_transfer_events": resource_transfers_total_mean,
        },
        "passed": cross_exchange_passed,
    }

    mint = aggregate.get("mint_submissions", {})
    checks["mint_submissions_mean"] = {
        "target": ">= 3.0",
        "observed": mint.get("mean"),
        "passed": isinstance(mint.get("mean"), float) and float(mint["mean"]) >= 3.0,
    }

    decision_success = aggregate.get("decision_success_rate", {})
    checks["decision_success_rate_min"] = {
        "target": ">= 0.98",
        "observed": decision_success.get("min"),
        "passed": isinstance(decision_success.get("min"), float) and float(decision_success["min"]) >= 0.98,
    }

    repeat_error = aggregate.get("repeat_error_rate", {})
    checks["repeat_error_rate_max"] = {
        "target": "<= 0.0",
        "observed": repeat_error.get("max"),
        "passed": isinstance(repeat_error.get("max"), float) and float(repeat_error["max"]) <= 0.0,
    }

    passed = all(item.get("passed") is True for item in checks.values())
    return {"passed": passed, "checks": checks}


def _metrics_from_summary(summary: dict[str, Any]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for key in NUMERIC_METRICS:
        value = summary.get(key)
        if isinstance(value, (int, float)):
            metrics[key] = float(value)
    return metrics


def _format_run_completion(
    *,
    index: int,
    runs: int,
    run_id: str,
    summary: dict[str, Any],
) -> str:
    llm_calls = int(summary.get("llm_calls", 0))
    forced_explore_rate = float(summary.get("forced_explore_rate", 0.0))
    cross_paid_consumption_amount = float(summary.get("cross_paid_consumption_amount", 0.0))
    return (
        "[scarcity-matrix] completed "
        f"run={index}/{runs} "
        f"ae3_run_id={run_id} "
        f"llm_calls={llm_calls} "
        f"forced_explore_rate={forced_explore_rate:.4f} "
        f"cross_paid_consumption_amount={cross_paid_consumption_amount:.4f}"
    )


def _build_matrix_gate_signals(payload: dict[str, Any]) -> dict[str, float]:
    signals: dict[str, float] = {}
    for key in ("runs", "runs_included_in_aggregate", "runs_excluded_from_aggregate"):
        value = payload.get(key)
        if isinstance(value, (int, float)):
            signals[key] = float(value)

    preflight = payload.get("preflight")
    if isinstance(preflight, dict):
        signals["llm_preflight_enabled"] = 1.0 if preflight.get("enabled") else 0.0
        signals["llm_preflight_success"] = 1.0 if preflight.get("success") else 0.0

    kpi_lock = payload.get("kpi_lock")
    if isinstance(kpi_lock, dict):
        signals["kpi_lock_passed"] = 1.0 if kpi_lock.get("passed") else 0.0

    aggregate = payload.get("aggregate")
    if isinstance(aggregate, dict):
        for metric, stats in aggregate.items():
            if not isinstance(metric, str) or not isinstance(stats, dict):
                continue
            for stat_name in ("mean", "stdev", "min", "max"):
                value = stats.get(stat_name)
                if isinstance(value, (int, float)):
                    signals[f"{metric}_{stat_name}"] = float(value)
                    if stat_name == "mean":
                        # Convenience alias for gate policies that use metric names directly.
                        signals[metric] = float(value)

    return signals


def _evaluate_matrix_gate_policy(
    *,
    policy: str | dict[str, Any],
    llm_client_repo: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if llm_client_repo:
        candidate = Path(llm_client_repo).expanduser().resolve()
        if candidate.exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
    experiment_eval = _load_experiment_eval_module()
    parsed_policy = experiment_eval.load_gate_policy(policy)
    signals = _build_matrix_gate_signals(payload)
    return {
        "policy": parsed_policy,
        "result": experiment_eval.evaluate_gate_policy(policy=parsed_policy, signals=signals),
    }


def _resolve_llm_preflight_enabled(
    *,
    mode: str,
    llm_loop_enabled: bool,
    target_llm_calls: int,
    min_llm_calls: int,
) -> bool:
    normalized = str(mode).strip().lower()
    if normalized not in {"auto", "on", "off"}:
        raise ValueError("--llm-preflight must be one of: auto, on, off")
    if normalized == "on":
        return True
    if normalized == "off":
        return False
    return bool(llm_loop_enabled and (target_llm_calls > 0 or min_llm_calls > 0))


def _resolve_llm_validity_thresholds(
    *,
    llm_loop_enabled: bool,
    target_llm_calls: int,
    min_llm_calls: int | None,
    min_llm_valid_decisions: int | None,
    min_llm_attempt_rate: float | None,
    min_llm_valid_decision_rate: float | None,
) -> dict[str, float | int]:
    resolved_min_llm_calls = int(min_llm_calls) if min_llm_calls is not None else 0
    if min_llm_calls is None and llm_loop_enabled and target_llm_calls > 0:
        resolved_min_llm_calls = 1
    resolved_min_llm_valid_decisions = int(min_llm_valid_decisions) if min_llm_valid_decisions is not None else 0
    resolved_min_llm_attempt_rate = float(min_llm_attempt_rate) if min_llm_attempt_rate is not None else 0.0
    resolved_min_llm_valid_decision_rate = (
        float(min_llm_valid_decision_rate) if min_llm_valid_decision_rate is not None else 0.0
    )

    if resolved_min_llm_calls < 0:
        raise ValueError("--min-llm-calls must be >= 0")
    if resolved_min_llm_valid_decisions < 0:
        raise ValueError("--min-llm-valid-decisions must be >= 0")
    if not 0.0 <= resolved_min_llm_attempt_rate <= 1.0:
        raise ValueError("--min-llm-attempt-rate must be within [0, 1]")
    if not 0.0 <= resolved_min_llm_valid_decision_rate <= 1.0:
        raise ValueError("--min-llm-valid-decision-rate must be within [0, 1]")

    return {
        "min_llm_calls": resolved_min_llm_calls,
        "min_llm_valid_decisions": resolved_min_llm_valid_decisions,
        "min_llm_attempt_rate": resolved_min_llm_attempt_rate,
        "min_llm_valid_decision_rate": resolved_min_llm_valid_decision_rate,
    }


def _evaluate_llm_engagement_validity(
    summary: dict[str, Any],
    run_meta: dict[str, Any],
    *,
    thresholds: dict[str, float | int],
) -> dict[str, Any]:
    llm_calls = int(summary.get("llm_calls", run_meta.get("llm_calls_observed", 0)) or 0)
    llm_valid_decision_total = int(summary.get("llm_valid_decision_total", 0) or 0)
    llm_attempt_rate = float(summary.get("llm_attempt_rate", 0.0) or 0.0)
    llm_valid_decision_rate = float(summary.get("llm_valid_decision_rate", 0.0) or 0.0)
    checks: dict[str, dict[str, Any]] = {
        "min_llm_calls": {
            "threshold": int(thresholds["min_llm_calls"]),
            "observed": llm_calls,
            "passed": llm_calls >= int(thresholds["min_llm_calls"]),
        },
        "min_llm_valid_decisions": {
            "threshold": int(thresholds["min_llm_valid_decisions"]),
            "observed": llm_valid_decision_total,
            "passed": llm_valid_decision_total >= int(thresholds["min_llm_valid_decisions"]),
        },
        "min_llm_attempt_rate": {
            "threshold": float(thresholds["min_llm_attempt_rate"]),
            "observed": llm_attempt_rate,
            "passed": llm_attempt_rate >= float(thresholds["min_llm_attempt_rate"]),
        },
        "min_llm_valid_decision_rate": {
            "threshold": float(thresholds["min_llm_valid_decision_rate"]),
            "observed": llm_valid_decision_rate,
            "passed": llm_valid_decision_rate >= float(thresholds["min_llm_valid_decision_rate"]),
        },
    }
    failed_checks = [name for name, detail in checks.items() if detail["passed"] is not True]
    return {
        "valid": not failed_checks,
        "failed_checks": failed_checks,
        "checks": checks,
    }


def _run_llm_preflight(cfg: AppConfig) -> dict[str, Any]:
    preflight_cfg = cfg.model_copy(deep=True)
    preflight_world = World(preflight_cfg)
    payer_id = preflight_world.principal_ids[0]
    result = preflight_world.call_llm_as_syscall(
        payer_id=payer_id,
        model=preflight_cfg.llm.default_model,
        messages=[
            {"role": "system", "content": "Return valid JSON and no prose."},
            {"role": "user", "content": '{"ok": true}'},
        ],
    )
    success = bool(result.get("success", False))
    payload: dict[str, Any] = {
        "enabled": True,
        "success": success,
        "model": preflight_cfg.llm.default_model,
        "payer_id": payer_id,
        "llm_calls_observed": int(preflight_world.get_llm_syscall_count()),
    }
    if success:
        payload["cost"] = float(result.get("cost", 0.0) or 0.0)
        payload["charged_cost"] = float(result.get("charged_cost", 0.0) or 0.0)
    else:
        payload["error"] = str(result.get("error", "llm preflight failed"))
        error_code = result.get("error_code")
        if isinstance(error_code, str) and error_code:
            payload["error_code"] = error_code
    return payload


def _build_config(
    *,
    config_path: str,
    agents: int,
    llm_loop: bool,
    loop_llm_cooldown: float,
    loop_forced_explore_mode: str | None,
    loop_policy_seed: int,
    loop_prompt_template_path: str | None,
    model_override: str | None,
    subscription_estimated_cost_multiplier: float | None,
) -> AppConfig:
    cfg = load_config(config_path)
    if agents <= 0:
        raise ValueError("--agents must be > 0")
    if loop_llm_cooldown < 0:
        raise ValueError("--loop-llm-cooldown must be >= 0")
    cfg.principals.count = int(agents)
    cfg.llm.enable_bootstrap_loop_llm = bool(llm_loop)
    cfg.llm.loop_llm_cooldown_seconds = float(loop_llm_cooldown)
    cfg.llm.loop_policy_seed = int(loop_policy_seed)
    if loop_forced_explore_mode is not None:
        mode = str(loop_forced_explore_mode).strip().lower()
        if mode not in {"baseline", "reduced", "off"}:
            raise ValueError("--loop-forced-explore must be one of: baseline, reduced, off")
        cfg.llm.loop_forced_explore_mode = cast(Literal["baseline", "reduced", "off"], mode)
    if loop_prompt_template_path is not None:
        template_path = str(loop_prompt_template_path).strip()
        if not template_path:
            raise ValueError("--loop-prompt-template must be a non-empty string path")
        cfg.llm.loop_prompt_template_path = template_path
    if model_override:
        model = str(model_override).strip()
        if not model:
            raise ValueError("--model must be a non-empty string")
        cfg.llm.default_model = model
        if cfg.llm.allowed_models and model not in cfg.llm.allowed_models:
            cfg.llm.allowed_models.append(model)
    if subscription_estimated_cost_multiplier is not None:
        multiplier = float(subscription_estimated_cost_multiplier)
        if multiplier < 0:
            raise ValueError("--subscription-estimated-cost-multiplier must be >= 0")
        cfg.llm.subscription_estimated_cost_multiplier = multiplier
    return cfg


async def _run_until_llm_calls(
    runner: SimulationRunner,
    *,
    target_duration: float,
    target_llm_calls: int,
) -> tuple[World, str]:
    run_task = asyncio.create_task(runner.run(target_duration))
    stop_reason = "duration_reached"
    try:
        while not run_task.done():
            if runner.world.get_llm_syscall_count() >= target_llm_calls:
                stop_reason = "llm_call_target_reached"
                runner.stop()
                break
            await asyncio.sleep(0.1)
        world = await run_task
    finally:
        if not run_task.done():
            runner.stop()
            world = await run_task
    if stop_reason != "llm_call_target_reached" and world.get_llm_syscall_count() >= target_llm_calls:
        stop_reason = "llm_call_target_reached"
    return world, stop_reason


def _run_single(
    cfg: AppConfig,
    duration: float,
    *,
    target_llm_calls: int,
) -> tuple[str, Path, dict[str, Any], dict[str, Any]]:
    if duration <= 0:
        raise ValueError("--duration must be > 0")
    world = World(cfg.model_copy(deep=True))
    runner = SimulationRunner(world)
    stop_reason = "duration_reached"
    if target_llm_calls > 0:
        world, stop_reason = asyncio.run(
            _run_until_llm_calls(
                runner,
                target_duration=duration,
                target_llm_calls=target_llm_calls,
            )
        )
    else:
        asyncio.run(runner.run(duration))
    events_path = Path(world.logger.output_path)
    summary = summarize_events(events_path)
    run_meta = {
        "elapsed_seconds": round(float(runner.elapsed_seconds), 6),
        "stop_reason": stop_reason,
        "target_llm_calls": int(target_llm_calls),
        "llm_calls_observed": int(world.get_llm_syscall_count()),
        "llm_calls_target_reached": bool(target_llm_calls > 0 and world.get_llm_syscall_count() >= target_llm_calls),
    }
    return world.run_id, events_path, summary, run_meta


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run repeated scarcity-first AE3 simulations and aggregate metrics.")
    parser.add_argument("--config", default="config/config.yaml", help="Path to AE3 config YAML")
    parser.add_argument("--runs", type=int, default=5, help="Number of runs")
    parser.add_argument("--duration", type=float, default=30.0, help="Seconds per run")
    parser.add_argument("--agents", type=int, default=4, help="Principal count override")
    parser.add_argument("--model", default=None, help="Override llm.default_model for matrix runs")
    parser.add_argument(
        "--subscription-estimated-cost-multiplier",
        type=float,
        default=None,
        help="Override llm.subscription_estimated_cost_multiplier for matrix runs",
    )
    parser.add_argument("--llm-loop", choices=("on", "off"), default="on", help="Enable/disable loop LLM")
    parser.add_argument("--loop-llm-cooldown", type=float, default=0.0, help="Loop LLM cooldown override")
    parser.add_argument(
        "--loop-forced-explore",
        choices=("baseline", "reduced", "off"),
        default=None,
        help="Loop forced-explore mode override",
    )
    parser.add_argument(
        "--loop-prompt-template",
        default=None,
        help="Override llm.loop_prompt_template_path for matrix runs",
    )
    parser.add_argument(
        "--target-llm-calls",
        type=int,
        default=0,
        help="If >0, stop each run once this many successful llm_syscall events are observed (duration is safety cap)",
    )
    parser.add_argument("--seed-base", type=int, default=0, help="Base loop-policy seed for matched-condition runs")
    parser.add_argument("--seed-step", type=int, default=1, help="Per-run increment for loop-policy seed")
    parser.add_argument(
        "--llm-preflight",
        choices=("auto", "on", "off"),
        default="auto",
        help="Run an LLM syscall preflight before the matrix (auto when LLM engagement thresholds apply)",
    )
    parser.add_argument(
        "--min-llm-calls",
        type=int,
        default=None,
        help="Minimum successful llm_syscall count required for a run to be valid",
    )
    parser.add_argument(
        "--min-llm-valid-decisions",
        type=int,
        default=None,
        help="Minimum llm_valid loop decisions required for a run to be valid",
    )
    parser.add_argument(
        "--min-llm-attempt-rate",
        type=float,
        default=None,
        help="Minimum llm_attempt_rate required for a run to be valid",
    )
    parser.add_argument(
        "--min-llm-valid-decision-rate",
        type=float,
        default=None,
        help="Minimum llm_valid_decision_rate required for a run to be valid",
    )
    parser.add_argument(
        "--invalid-run-policy",
        choices=("warn", "drop", "fail"),
        default="warn",
        help="Handling for runs that fail LLM engagement validity thresholds",
    )
    parser.add_argument("--log-experiment", action="store_true", help="Log each run summary into llm_client experiments")
    parser.add_argument("--experiment-dataset", default="agent_ecology3_emergence", help="llm_client dataset label")
    parser.add_argument("--experiment-project", default="agent_ecology3", help="llm_client project label")
    parser.add_argument("--experiment-model", default=None, help="Override experiment model label")
    parser.add_argument("--experiment-condition-id", default=None, help="Condition label for cohort comparison")
    parser.add_argument("--experiment-scenario-id", default=None, help="Scenario label grouping related matrix runs")
    parser.add_argument("--experiment-phase", default=None, help="Experiment phase label for cohort filtering")
    parser.add_argument(
        "--llm-client-repo",
        default=os.environ.get("LLM_CLIENT_REPO", DEFAULT_LLM_CLIENT_REPO),
        help="Path to llm_client repo for import fallback",
    )
    parser.add_argument("--output-dir", default="logs", help="Output directory for matrix artifacts")
    parser.add_argument("--prefix", default="scarcity_baseline_matrix", help="Output file prefix")
    parser.add_argument("--skip-kpi-check", action="store_true", help="Skip KPI lock evaluation")
    parser.add_argument(
        "--gate-policy",
        default=None,
        help="Gate policy JSON string/path evaluated against matrix-level aggregate signals",
    )
    parser.add_argument(
        "--gate-fail-exit-code",
        action="store_true",
        help="Exit with code 2 when --gate-policy evaluates to FAIL",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print final JSON payload")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    runs = max(1, int(args.runs))
    llm_loop_enabled = str(args.llm_loop).strip().lower() == "on"

    cfg = _build_config(
        config_path=args.config,
        agents=int(args.agents),
        llm_loop=llm_loop_enabled,
        loop_llm_cooldown=float(args.loop_llm_cooldown),
        loop_forced_explore_mode=args.loop_forced_explore,
        loop_policy_seed=int(args.seed_base),
        loop_prompt_template_path=args.loop_prompt_template,
        model_override=args.model,
        subscription_estimated_cost_multiplier=args.subscription_estimated_cost_multiplier,
    )
    target_llm_calls = int(args.target_llm_calls)
    if target_llm_calls < 0:
        raise ValueError("--target-llm-calls must be >= 0")
    seed_step = int(args.seed_step)
    if seed_step < 0:
        raise ValueError("--seed-step must be >= 0")

    validity_thresholds = _resolve_llm_validity_thresholds(
        llm_loop_enabled=llm_loop_enabled,
        target_llm_calls=target_llm_calls,
        min_llm_calls=args.min_llm_calls,
        min_llm_valid_decisions=args.min_llm_valid_decisions,
        min_llm_attempt_rate=args.min_llm_attempt_rate,
        min_llm_valid_decision_rate=args.min_llm_valid_decision_rate,
    )
    preflight_enabled = _resolve_llm_preflight_enabled(
        mode=str(args.llm_preflight),
        llm_loop_enabled=llm_loop_enabled,
        target_llm_calls=target_llm_calls,
        min_llm_calls=int(validity_thresholds["min_llm_calls"]),
    )
    preflight: dict[str, Any] = {"mode": str(args.llm_preflight), "enabled": preflight_enabled}
    if preflight_enabled:
        preflight = {
            **preflight,
            **_run_llm_preflight(cfg),
        }
        if preflight.get("success") is not True:
            raise RuntimeError(f"LLM preflight failed: {preflight.get('error', 'unknown error')}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    jsonl_path = output_dir / f"{args.prefix}_{stamp}.jsonl"
    summary_path = output_dir / f"{args.prefix}_{stamp}_summary.json"
    run_ids_path = output_dir / f"{args.prefix}_{stamp}_run_ids.txt"
    experiment_condition_id = str(args.experiment_condition_id).strip() if args.experiment_condition_id else None
    experiment_scenario_id = str(args.experiment_scenario_id).strip() if args.experiment_scenario_id else None
    experiment_phase = str(args.experiment_phase).strip() if args.experiment_phase else None

    rows: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, Any]] = []
    with jsonl_path.open("w", encoding="utf-8") as matrix_stream, run_ids_path.open("w", encoding="utf-8") as run_stream:
        for idx in range(1, runs + 1):
            print(f"[scarcity-matrix] run {idx}/{runs}", flush=True)
            run_seed = int(args.seed_base) + ((idx - 1) * seed_step)
            run_cfg = cfg.model_copy(deep=True)
            run_cfg.llm.loop_policy_seed = run_seed
            run_id, events_path, summary, run_meta = _run_single(
                run_cfg,
                float(args.duration),
                target_llm_calls=target_llm_calls,
            )
            run_meta["loop_policy_seed"] = run_seed
            run_stream.write(run_id + "\n")
            run_stream.flush()

            experiment_run_id: str | None = None
            experiment_finish: dict[str, Any] | None = None
            if args.log_experiment:
                experiment_finish = _log_summary_to_llm_client(
                    summary=summary,
                    events_path=events_path,
                    ae3_run_id=run_id,
                    dataset=args.experiment_dataset,
                    project=args.experiment_project,
                    model=args.experiment_model,
                    llm_client_repo=args.llm_client_repo,
                    experiment_run_id=None,
                    condition_id=experiment_condition_id,
                    seed=run_seed,
                    replicate=idx,
                    scenario_id=experiment_scenario_id,
                    phase=experiment_phase,
                )
                experiment_run_id_raw = experiment_finish.get("run_id")
                if isinstance(experiment_run_id_raw, str):
                    experiment_run_id = experiment_run_id_raw

            llm_validity = _evaluate_llm_engagement_validity(
                summary,
                run_meta,
                thresholds=validity_thresholds,
            )
            include_in_aggregate = True
            if llm_validity["valid"] is not True:
                invalid_msg = (
                    f"[scarcity-matrix] invalid llm engagement run={run_id} "
                    f"failed={','.join(llm_validity['failed_checks']) or 'unknown'}"
                )
                if args.invalid_run_policy == "fail":
                    raise RuntimeError(invalid_msg)
                if args.invalid_run_policy == "drop":
                    include_in_aggregate = False
                    print(f"{invalid_msg} (dropped)", flush=True)
                else:
                    print(f"{invalid_msg} (included)", flush=True)

            record = {
                "ae3_run_id": run_id,
                "events_path": str(events_path),
                "experiment_run_id": experiment_run_id,
                "condition_id": experiment_condition_id,
                "seed": run_seed,
                "replicate": idx,
                "scenario_id": experiment_scenario_id,
                "phase": experiment_phase,
                "run_meta": run_meta,
                "metrics": _metrics_from_summary(summary),
                "llm_validity": llm_validity,
                "included_in_aggregate": include_in_aggregate,
            }
            rows.append(record)
            if include_in_aggregate:
                aggregate_rows.append(record)
            matrix_stream.write(
                json.dumps(
                    {
                        "summary": summary,
                        "experiment_run": experiment_finish,
                        "record": record,
                    },
                    ensure_ascii=True,
                )
                + "\n"
            )
            matrix_stream.flush()
            print(_format_run_completion(index=idx, runs=runs, run_id=run_id, summary=summary), flush=True)

    aggregate = aggregate_metrics(aggregate_rows)
    payload: dict[str, Any] = {
        "matrix_type": "scarcity_first_baseline",
        "runs": runs,
        "runs_included_in_aggregate": len(aggregate_rows),
        "runs_excluded_from_aggregate": runs - len(aggregate_rows),
        "settings": {
            "duration": float(args.duration),
            "agents": int(args.agents),
            "model": str(cfg.llm.default_model),
            "llm_loop": llm_loop_enabled,
            "loop_llm_cooldown": float(args.loop_llm_cooldown),
            "loop_forced_explore_mode": str(cfg.llm.loop_forced_explore_mode),
            "loop_prompt_template_path": cfg.llm.loop_prompt_template_path,
            "target_llm_calls": target_llm_calls,
            "seed_base": int(args.seed_base),
            "seed_step": seed_step,
            "subscription_estimated_cost_multiplier": float(cfg.llm.subscription_estimated_cost_multiplier),
            "llm_preflight": str(args.llm_preflight),
            "llm_validity_thresholds": validity_thresholds,
            "invalid_run_policy": str(args.invalid_run_policy),
            "log_experiment": bool(args.log_experiment),
            "experiment_condition_id": experiment_condition_id,
            "experiment_scenario_id": experiment_scenario_id,
            "experiment_phase": experiment_phase,
        },
        "preflight": preflight,
        "run_records": rows,
        "aggregate": aggregate,
        "source_jsonl": str(jsonl_path.resolve()),
        "run_ids_file": str(run_ids_path.resolve()),
    }
    if not args.skip_kpi_check:
        payload["kpi_lock"] = evaluate_kpi_lock(aggregate)

    gate_evaluation: dict[str, Any] | None = None
    if args.gate_policy:
        gate_evaluation = _evaluate_matrix_gate_policy(
            policy=args.gate_policy,
            llm_client_repo=args.llm_client_repo,
            payload=payload,
        )
        payload["gate_policy"] = gate_evaluation["policy"]
        payload["gate_result"] = gate_evaluation["result"]

    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    payload["summary_path"] = str(summary_path.resolve())

    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
    else:
        print(json.dumps(payload, sort_keys=True), flush=True)
    if gate_evaluation is not None and gate_evaluation["result"].get("passed") is not True and args.gate_fail_exit_code:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
