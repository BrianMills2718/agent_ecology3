"""Compare two phase1 suite outputs with aggregate and matched-seed deltas."""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_METRICS: tuple[str, ...] = (
    "llm_calls",
    "llm_valid_decision_rate",
    "forced_explore_rate",
    "loop_action_entropy_bits",
    "cross_paid_consumption_amount",
    "cross_transfer_amount",
    "mint_submissions",
    "decision_success_rate",
    "reuse_weighted_artifact_value_total",
    "resource_transfers_total",
    "llm_budget_transfer_amount",
    "llm_cost",
)


def _parse_csv(raw: str | None) -> list[str]:
    if raw is None:
        return []
    values = [item.strip() for item in raw.split(",") if item.strip()]
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _metric_mean(summary: dict[str, Any], metric: str) -> float:
    aggregate = summary.get("aggregate")
    if not isinstance(aggregate, dict):
        return 0.0
    stats = aggregate.get(metric)
    if not isinstance(stats, dict):
        return 0.0
    value = stats.get("mean")
    return float(value) if isinstance(value, (int, float)) else 0.0


def _seed_metric_map(summary: dict[str, Any], metric: str) -> dict[int, float]:
    out: dict[int, float] = {}
    run_records = summary.get("run_records")
    if not isinstance(run_records, list):
        return out
    for row in run_records:
        if not isinstance(row, dict):
            continue
        seed = row.get("seed")
        metrics = row.get("metrics")
        if not isinstance(seed, int) or not isinstance(metrics, dict):
            continue
        value = metrics.get(metric)
        if isinstance(value, (int, float)):
            out[int(seed)] = float(value)
    return out


def _load_suite_by_condition(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"suite payload must be an object: {path}")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError(f"suite records must be a list: {path}")
    out: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        condition = record.get("condition")
        summary = record.get("summary")
        if isinstance(condition, str) and isinstance(summary, dict):
            out[condition] = summary
    if not out:
        raise ValueError(f"no condition summaries found in suite: {path}")
    return out


def compare_suite_files(
    *,
    baseline_suite: Path,
    candidate_suite: Path,
    metrics: list[str] | None = None,
    conditions: list[str] | None = None,
) -> dict[str, Any]:
    baseline_by_condition = _load_suite_by_condition(baseline_suite)
    candidate_by_condition = _load_suite_by_condition(candidate_suite)
    metric_list = metrics if metrics else list(DEFAULT_METRICS)

    if conditions:
        condition_list = [item for item in conditions if item in baseline_by_condition and item in candidate_by_condition]
    else:
        condition_list = [
            item for item in ("baseline", "reduced", "off") if item in baseline_by_condition and item in candidate_by_condition
        ]
        if not condition_list:
            condition_list = sorted(set(baseline_by_condition).intersection(candidate_by_condition))

    if not condition_list:
        raise ValueError("no overlapping conditions between suites")

    aggregate_deltas: dict[str, dict[str, dict[str, float]]] = {}
    matched_seed_deltas: dict[str, dict[str, dict[str, Any]]] = {}
    gates: dict[str, dict[str, Any]] = {}
    strengths: list[str] = []
    risks: list[str] = []
    uncertainties: list[str] = []

    def _delta(aggregate_metrics: dict[str, dict[str, float]], metric: str) -> float:
        row = aggregate_metrics.get(metric, {})
        value = row.get("delta")
        return float(value) if isinstance(value, (int, float)) else 0.0

    for condition in condition_list:
        baseline_summary = baseline_by_condition[condition]
        candidate_summary = candidate_by_condition[condition]
        condition_aggregate: dict[str, dict[str, float]] = {}
        condition_matched: dict[str, dict[str, Any]] = {}

        for metric in metric_list:
            baseline_value = _metric_mean(baseline_summary, metric)
            candidate_value = _metric_mean(candidate_summary, metric)
            condition_aggregate[metric] = {
                "baseline": baseline_value,
                "candidate": candidate_value,
                "delta": candidate_value - baseline_value,
            }

            baseline_seed_map = _seed_metric_map(baseline_summary, metric)
            candidate_seed_map = _seed_metric_map(candidate_summary, metric)
            shared_seeds = sorted(set(baseline_seed_map).intersection(candidate_seed_map))
            seed_deltas = [
                {"seed": seed, "delta": candidate_seed_map[seed] - baseline_seed_map[seed]} for seed in shared_seeds
            ]
            deltas = [row["delta"] for row in seed_deltas]
            condition_matched[metric] = {
                "count": len(deltas),
                "mean_delta": round(statistics.fmean(deltas), 6) if deltas else 0.0,
                "stdev_delta": round(statistics.pstdev(deltas), 6) if len(deltas) > 1 else 0.0,
                "seed_deltas": seed_deltas,
            }

        aggregate_deltas[condition] = condition_aggregate
        matched_seed_deltas[condition] = condition_matched
        gates[condition] = {
            "baseline_gate_passed": bool(baseline_summary.get("gate_result", {}).get("passed")),
            "candidate_gate_passed": bool(candidate_summary.get("gate_result", {}).get("passed")),
            "baseline_runs_included": int(baseline_summary.get("runs_included_in_aggregate", 0) or 0),
            "candidate_runs_included": int(candidate_summary.get("runs_included_in_aggregate", 0) or 0),
        }

        validity_delta = _delta(condition_aggregate, "llm_valid_decision_rate")
        forced_delta = _delta(condition_aggregate, "forced_explore_rate")
        paid_delta = _delta(condition_aggregate, "cross_paid_consumption_amount")
        reuse_delta = _delta(condition_aggregate, "reuse_weighted_artifact_value_total")
        transfer_delta = _delta(condition_aggregate, "cross_transfer_amount")

        if paid_delta > 0.5 and reuse_delta > 1.0:
            strengths.append(
                f"{condition}: candidate increases paid consumption (+{paid_delta:.3f}) and reuse value (+{reuse_delta:.3f})"
            )
        if validity_delta < -0.05:
            risks.append(
                f"{condition}: candidate lowers llm_valid_decision_rate by {abs(validity_delta):.3f}"
            )
        if forced_delta > 0.05:
            risks.append(
                f"{condition}: candidate raises forced_explore_rate by {forced_delta:.3f}"
            )
        if transfer_delta < -1.0 and paid_delta > 0.5:
            uncertainties.append(
                f"{condition}: trade shifted from direct transfers to priced consumption; causal quality still uncertain"
            )

    if not strengths:
        uncertainties.append("No strong candidate improvement signal exceeded current heuristic thresholds.")

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_suite": str(baseline_suite.resolve()),
        "candidate_suite": str(candidate_suite.resolve()),
        "conditions": condition_list,
        "metrics": metric_list,
        "aggregate_deltas": aggregate_deltas,
        "matched_seed_deltas": matched_seed_deltas,
        "gates": gates,
        "advisory": {
            "strengths": strengths,
            "risks": risks,
            "uncertainties": uncertainties,
        },
    }
    return payload


def _print_table(payload: dict[str, Any]) -> None:
    print("condition\tmetric\tbaseline\tcandidate\tdelta")
    aggregate = payload.get("aggregate_deltas", {})
    metrics = payload.get("metrics", [])
    for condition in payload.get("conditions", []):
        condition_data = aggregate.get(condition, {})
        if not isinstance(condition_data, dict):
            continue
        for metric in metrics:
            metric_data = condition_data.get(metric, {})
            if not isinstance(metric_data, dict):
                continue
            baseline_value = float(metric_data.get("baseline", 0.0))
            candidate_value = float(metric_data.get("candidate", 0.0))
            delta = float(metric_data.get("delta", 0.0))
            print(f"{condition}\t{metric}\t{baseline_value:.6g}\t{candidate_value:.6g}\t{delta:.6g}")

    print("\nmatched_seed_mean_delta")
    print("condition\tmetric\tcount\tmean_delta\tstdev_delta")
    matched = payload.get("matched_seed_deltas", {})
    for condition in payload.get("conditions", []):
        condition_data = matched.get(condition, {})
        if not isinstance(condition_data, dict):
            continue
        for metric in metrics:
            metric_data = condition_data.get(metric, {})
            if not isinstance(metric_data, dict):
                continue
            count = int(metric_data.get("count", 0))
            mean_delta = float(metric_data.get("mean_delta", 0.0))
            stdev_delta = float(metric_data.get("stdev_delta", 0.0))
            print(f"{condition}\t{metric}\t{count}\t{mean_delta:.6g}\t{stdev_delta:.6g}")

    advisory = payload.get("advisory", {})
    print("\nadvisory")
    for key in ("strengths", "risks", "uncertainties"):
        values = advisory.get(key, [])
        if not isinstance(values, list):
            continue
        if not values:
            print(f"{key}: none")
            continue
        for item in values:
            print(f"{key}: {item}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two phase1 suite outputs.")
    parser.add_argument("--baseline-suite", required=True, help="Path to baseline suite JSON.")
    parser.add_argument("--candidate-suite", required=True, help="Path to candidate suite JSON.")
    parser.add_argument("--metrics", default=",".join(DEFAULT_METRICS), help="Comma-separated metric list.")
    parser.add_argument("--conditions", default=None, help="Optional comma-separated condition list.")
    parser.add_argument("--output", default=None, help="Optional path to write JSON payload.")
    parser.add_argument("--pretty", action="store_true", help="Print JSON payload in addition to table.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    metrics = _parse_csv(args.metrics)
    conditions = _parse_csv(args.conditions) if args.conditions else None
    payload = compare_suite_files(
        baseline_suite=Path(args.baseline_suite),
        candidate_suite=Path(args.candidate_suite),
        metrics=metrics,
        conditions=conditions,
    )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

    _print_table(payload)
    if args.pretty:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
