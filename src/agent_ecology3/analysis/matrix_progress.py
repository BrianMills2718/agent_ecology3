"""Summarize partial scarcity-matrix JSONL output while a run is in progress."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .scarcity_matrix import NUMERIC_METRICS, aggregate_metrics


def _coerce_record(entry: dict[str, Any]) -> dict[str, Any] | None:
    record = entry.get("record")
    if isinstance(record, dict):
        return record
    summary = entry.get("summary")
    if not isinstance(summary, dict):
        return None
    metrics: dict[str, float] = {}
    for key in NUMERIC_METRICS:
        value = summary.get(key)
        if isinstance(value, (int, float)):
            metrics[key] = float(value)
    return {
        "ae3_run_id": summary.get("run_id"),
        "metrics": metrics,
    }


def load_progress_rows(path: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    malformed = 0
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if not isinstance(entry, dict):
            malformed += 1
            continue
        record = _coerce_record(entry)
        if record is None:
            malformed += 1
            continue
        rows.append(record)
    return rows, malformed


def summarize_progress(rows: list[dict[str, Any]]) -> dict[str, Any]:
    aggregate = aggregate_metrics(rows)
    last = rows[-1] if rows else {}
    metrics_raw = last.get("metrics")
    last_metrics: dict[str, Any] = metrics_raw if isinstance(metrics_raw, dict) else {}
    return {
        "runs_completed": len(rows),
        "aggregate": aggregate,
        "last_run": {
            "ae3_run_id": last.get("ae3_run_id"),
            "seed": last.get("seed"),
            "replicate": last.get("replicate"),
            "llm_calls": last_metrics.get("llm_calls"),
            "forced_explore_rate": last_metrics.get("forced_explore_rate"),
            "cross_paid_consumption_amount": last_metrics.get("cross_paid_consumption_amount"),
            "reuse_weighted_artifact_value_total": last_metrics.get("reuse_weighted_artifact_value_total"),
            "llm_valid_decision_rate": last_metrics.get("llm_valid_decision_rate"),
        },
    }


def _parse_metrics(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    values = [item.strip() for item in raw.split(",") if item.strip()]
    if not values:
        return None
    return values


def _filter_aggregate_metrics(aggregate: dict[str, Any], metrics: list[str] | None) -> dict[str, Any]:
    if not metrics:
        return aggregate
    allowed = set(metrics)
    return {key: value for key, value in aggregate.items() if key in allowed}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize partial scarcity-matrix JSONL progress")
    parser.add_argument("--jsonl", required=True, help="Path to scarcity_matrix JSONL file")
    parser.add_argument(
        "--metrics",
        default=None,
        help="Optional comma-separated metric allow-list for aggregate output",
    )
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    jsonl_path = Path(str(args.jsonl)).expanduser().resolve()
    if not jsonl_path.exists():
        raise FileNotFoundError(f"jsonl file does not exist: {jsonl_path}")

    rows, malformed = load_progress_rows(jsonl_path)
    payload = {
        "jsonl_path": str(jsonl_path),
        "malformed_rows": malformed,
        **summarize_progress(rows),
    }
    metrics_filter = _parse_metrics(args.metrics)
    payload["aggregate"] = _filter_aggregate_metrics(payload.get("aggregate", {}), metrics_filter)

    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
