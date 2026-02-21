"""Run repeated scarcity-first simulations and aggregate emergence metrics."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

from ..config import AppConfig, load_config
from ..simulation import SimulationRunner
from ..world import World
from .emergence_report import _log_summary_to_llm_client, summarize_events


NUMERIC_METRICS: tuple[str, ...] = (
    "actions_total",
    "action_entropy_bits",
    "cross_read_events",
    "cross_transfer_amount",
    "resource_transfers_total",
    "llm_budget_transfer_amount",
    "cross_llm_budget_transfer_amount",
    "mint_submissions",
    "llm_calls",
    "llm_cost",
    "fallback_rate",
    "decision_success_rate",
    "repeat_error_rate",
)


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

    entropy = aggregate.get("action_entropy_bits", {})
    checks["action_entropy_bits_mean"] = {
        "target": ">= 2.1",
        "observed": entropy.get("mean"),
        "passed": isinstance(entropy.get("mean"), float) and float(entropy["mean"]) >= 2.1,
    }

    cross_transfer = aggregate.get("cross_transfer_amount", {})
    checks["cross_transfer_amount_mean"] = {
        "target": ">= 3.0",
        "observed": cross_transfer.get("mean"),
        "passed": isinstance(cross_transfer.get("mean"), float) and float(cross_transfer["mean"]) >= 3.0,
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


def _build_config(
    *,
    config_path: str,
    agents: int,
    llm_loop: bool,
    loop_llm_cooldown: float,
    model_override: str | None,
) -> AppConfig:
    cfg = load_config(config_path)
    if agents <= 0:
        raise ValueError("--agents must be > 0")
    if loop_llm_cooldown < 0:
        raise ValueError("--loop-llm-cooldown must be >= 0")
    cfg.principals.count = int(agents)
    cfg.llm.enable_bootstrap_loop_llm = bool(llm_loop)
    cfg.llm.loop_llm_cooldown_seconds = float(loop_llm_cooldown)
    if model_override:
        model = str(model_override).strip()
        if not model:
            raise ValueError("--model must be a non-empty string")
        cfg.llm.default_model = model
        if cfg.llm.allowed_models and model not in cfg.llm.allowed_models:
            cfg.llm.allowed_models.append(model)
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
    parser.add_argument("--llm-loop", choices=("on", "off"), default="on", help="Enable/disable loop LLM")
    parser.add_argument("--loop-llm-cooldown", type=float, default=0.0, help="Loop LLM cooldown override")
    parser.add_argument(
        "--target-llm-calls",
        type=int,
        default=0,
        help="If >0, stop each run once this many successful llm_syscall events are observed (duration is safety cap)",
    )
    parser.add_argument("--log-experiment", action="store_true", help="Log each run summary into llm_client experiments")
    parser.add_argument("--experiment-dataset", default="agent_ecology3_emergence", help="llm_client dataset label")
    parser.add_argument("--experiment-project", default="agent_ecology3", help="llm_client project label")
    parser.add_argument("--experiment-model", default=None, help="Override experiment model label")
    parser.add_argument(
        "--llm-client-repo",
        default=os.environ.get("LLM_CLIENT_REPO", "/home/brian/projects/llm_client"),
        help="Path to llm_client repo for import fallback",
    )
    parser.add_argument("--output-dir", default="logs", help="Output directory for matrix artifacts")
    parser.add_argument("--prefix", default="scarcity_baseline_matrix", help="Output file prefix")
    parser.add_argument("--skip-kpi-check", action="store_true", help="Skip KPI lock evaluation")
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
        model_override=args.model,
    )
    target_llm_calls = int(args.target_llm_calls)
    if target_llm_calls < 0:
        raise ValueError("--target-llm-calls must be >= 0")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time())
    jsonl_path = output_dir / f"{args.prefix}_{stamp}.jsonl"
    summary_path = output_dir / f"{args.prefix}_{stamp}_summary.json"
    run_ids_path = output_dir / f"{args.prefix}_{stamp}_run_ids.txt"

    rows: list[dict[str, Any]] = []
    with jsonl_path.open("w", encoding="utf-8") as matrix_stream, run_ids_path.open("w", encoding="utf-8") as run_stream:
        for idx in range(1, runs + 1):
            print(f"[scarcity-matrix] run {idx}/{runs}")
            run_id, events_path, summary, run_meta = _run_single(
                cfg,
                float(args.duration),
                target_llm_calls=target_llm_calls,
            )
            run_stream.write(run_id + "\n")

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
                )
                experiment_run_id_raw = experiment_finish.get("run_id")
                if isinstance(experiment_run_id_raw, str):
                    experiment_run_id = experiment_run_id_raw

            record = {
                "ae3_run_id": run_id,
                "events_path": str(events_path),
                "experiment_run_id": experiment_run_id,
                "run_meta": run_meta,
                "metrics": _metrics_from_summary(summary),
            }
            rows.append(record)
            matrix_stream.write(
                json.dumps(
                    {
                        "summary": summary,
                        "experiment_run": experiment_finish,
                    },
                    ensure_ascii=True,
                )
                + "\n"
            )

    aggregate = aggregate_metrics(rows)
    payload: dict[str, Any] = {
        "matrix_type": "scarcity_first_baseline",
        "runs": runs,
        "settings": {
            "duration": float(args.duration),
            "agents": int(args.agents),
            "model": str(cfg.llm.default_model),
            "llm_loop": llm_loop_enabled,
            "loop_llm_cooldown": float(args.loop_llm_cooldown),
            "target_llm_calls": target_llm_calls,
            "log_experiment": bool(args.log_experiment),
        },
        "run_records": rows,
        "aggregate": aggregate,
        "source_jsonl": str(jsonl_path.resolve()),
        "run_ids_file": str(run_ids_path.resolve()),
    }
    if not args.skip_kpi_check:
        payload["kpi_lock"] = evaluate_kpi_lock(aggregate)

    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    payload["summary_path"] = str(summary_path.resolve())

    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
