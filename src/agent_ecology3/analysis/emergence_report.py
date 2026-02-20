"""Compute emergence metrics from AE3 event logs and optionally log to llm_client experiments."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_ARTIFACT_OWNER_PREFIX = re.compile(r"^(alpha_\d+)_")


def _infer_owner(artifact_id: str, owner_map: dict[str, str]) -> str | None:
    owner = owner_map.get(artifact_id)
    if owner:
        return owner
    match = _ARTIFACT_OWNER_PREFIX.match(artifact_id)
    if match:
        return match.group(1)
    return None


def summarize_events(path: Path) -> dict[str, Any]:
    event_types: Counter[str] = Counter()
    action_types: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    query_types: Counter[str] = Counter()
    transfer_edges: Counter[tuple[str, str]] = Counter()
    read_edges: Counter[tuple[str, str]] = Counter()
    final_scrip: dict[str, int] = {}
    owner_map: dict[str, str] = {}
    per_principal_actions: Counter[str] = Counter()
    per_principal_errors: Counter[str] = Counter()
    per_principal_llm_calls: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()

    first_ts: str | None = None
    last_ts: str | None = None

    llm_calls = 0
    llm_cost = 0.0
    writes = 0
    reads_success = 0
    transfers = 0
    mint_submissions = 0
    kernel_queries_success = 0

    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            event = json.loads(raw)
            event_type = str(event.get("event_type", "unknown"))
            event_types[event_type] += 1

            timestamp = event.get("timestamp")
            if isinstance(timestamp, str):
                if first_ts is None:
                    first_ts = timestamp
                last_ts = timestamp

            if event_type == "llm_syscall":
                llm_calls += 1
                llm_cost += float(event.get("charged_cost") or 0.0)
                payer = event.get("payer_id")
                model = event.get("model")
                if isinstance(payer, str):
                    per_principal_llm_calls[payer] += 1
                if isinstance(model, str) and model:
                    model_counts[model] += 1
                continue

            if event_type == "artifact_written":
                writes += 1
                artifact_id = event.get("artifact_id")
                owner = event.get("owner")
                if isinstance(artifact_id, str) and isinstance(owner, str):
                    owner_map[artifact_id] = owner
                continue

            if event_type == "artifact_read":
                reads_success += 1
                principal = event.get("principal_id")
                artifact_id = event.get("artifact_id")
                if isinstance(principal, str) and isinstance(artifact_id, str):
                    owner = _infer_owner(artifact_id, owner_map)
                    if owner:
                        read_edges[(principal, owner)] += 1
                continue

            if event_type == "transfer":
                transfers += 1
                sender = event.get("sender")
                recipient = event.get("recipient")
                amount = int(event.get("amount") or 0)
                if isinstance(sender, str) and isinstance(recipient, str):
                    transfer_edges[(sender, recipient)] += amount
                continue

            if event_type == "mint_submission":
                mint_submissions += 1
                continue

            if event_type == "kernel_query":
                kernel_queries_success += 1
                continue

            if event_type != "action":
                continue

            intent = event.get("intent") or {}
            result = event.get("result") or {}
            action_type = str(intent.get("action_type", "unknown"))
            action_types[action_type] += 1

            principal = intent.get("principal_id")
            if isinstance(principal, str):
                per_principal_actions[principal] += 1

            if action_type == "query_kernel":
                query_type = intent.get("query_type")
                if isinstance(query_type, str):
                    query_types[query_type] += 1

            if not bool(result.get("success")):
                error_code = str(result.get("error_code") or "unknown")
                errors[error_code] += 1
                if isinstance(principal, str):
                    per_principal_errors[principal] += 1

            if isinstance(principal, str) and "scrip_after" in event:
                final_scrip[principal] = int(event["scrip_after"])

    action_total = sum(action_types.values())
    entropy_bits = 0.0
    if action_total > 0:
        for count in action_types.values():
            p = count / action_total
            entropy_bits -= p * math.log(p, 2)

    cross_read_events = sum(v for (src, dst), v in read_edges.items() if src != dst)
    cross_transfer_amount = sum(v for (src, dst), v in transfer_edges.items() if src != dst)

    principals = sorted(set(final_scrip) | set(per_principal_actions) | set(per_principal_llm_calls))
    per_principal: dict[str, dict[str, int]] = {}
    for principal in principals:
        per_principal[principal] = {
            "actions": int(per_principal_actions.get(principal, 0)),
            "errors": int(per_principal_errors.get(principal, 0)),
            "llm_calls": int(per_principal_llm_calls.get(principal, 0)),
            "final_scrip": int(final_scrip.get(principal, 0)),
        }

    dominant_model = model_counts.most_common(1)[0][0] if model_counts else "unknown"

    return {
        "events_total": sum(event_types.values()),
        "event_types": dict(event_types),
        "actions_total": action_total,
        "action_types": dict(action_types),
        "action_entropy_bits": round(entropy_bits, 3),
        "llm_calls": llm_calls,
        "llm_cost": round(llm_cost, 6),
        "writes": writes,
        "reads_success": reads_success,
        "transfers": transfers,
        "mint_submissions": mint_submissions,
        "kernel_queries_success": kernel_queries_success,
        "query_types": dict(query_types),
        "errors": dict(errors),
        "cross_read_events": cross_read_events,
        "cross_transfer_amount": cross_transfer_amount,
        "transfer_edges": {
            f"{src}->{dst}": amount for (src, dst), amount in sorted(transfer_edges.items())
        },
        "read_edges": {
            f"{src}->{dst}": count for (src, dst), count in sorted(read_edges.items())
        },
        "final_scrip": final_scrip,
        "per_principal": per_principal,
        "model_counts": dict(model_counts),
        "dominant_model": dominant_model,
        "started_at": first_ts,
        "ended_at": last_ts,
    }


def _resolve_events_path(log_path: str, run_id: str | None) -> Path:
    if run_id:
        return Path(log_path) / run_id / "events.jsonl"
    return Path(log_path)


def _ensure_llm_client_import(repo_path: str | None) -> None:
    if repo_path:
        repo = Path(repo_path)
        if repo.exists() and str(repo) not in sys.path:
            sys.path.insert(0, str(repo))


def _experiment_numeric_metrics(summary: dict[str, Any]) -> dict[str, float]:
    keys = (
        "action_entropy_bits",
        "actions_total",
        "llm_calls",
        "llm_cost",
        "writes",
        "reads_success",
        "transfers",
        "mint_submissions",
        "kernel_queries_success",
        "cross_read_events",
        "cross_transfer_amount",
    )
    out: dict[str, float] = {}
    for key in keys:
        value = summary.get(key)
        if isinstance(value, (int, float)):
            out[key] = float(value)
    return out


def _log_summary_to_llm_client(
    *,
    summary: dict[str, Any],
    events_path: Path,
    ae3_run_id: str | None,
    dataset: str,
    project: str,
    model: str | None,
    llm_client_repo: str | None,
    experiment_run_id: str | None,
) -> dict[str, Any]:
    _ensure_llm_client_import(llm_client_repo)
    from llm_client import finish_run, log_item, start_run

    experiment_model = model or str(summary.get("dominant_model") or "unknown")
    metrics = _experiment_numeric_metrics(summary)
    metrics_schema = list(metrics.keys())

    config = {
        "source": "agent_ecology3",
        "ae3_run_id": ae3_run_id,
        "events_path": str(events_path),
    }

    run_id = start_run(
        dataset=dataset,
        model=experiment_model,
        config=config,
        metrics_schema=metrics_schema,
        run_id=experiment_run_id,
        project=project,
        provenance={
            "agent_ecology3_run": ae3_run_id,
            "events_file": str(events_path),
        },
    )

    overall_extra = {
        "action_types": summary.get("action_types"),
        "errors": summary.get("errors"),
        "query_types": summary.get("query_types"),
        "model_counts": summary.get("model_counts"),
    }
    trace_id = f"ae3/{ae3_run_id}" if ae3_run_id else None
    log_item(
        run_id=run_id,
        item_id="overall",
        metrics=metrics,
        extra=overall_extra,
        cost=float(summary.get("llm_cost") or 0.0),
        trace_id=trace_id,
    )

    per_principal = summary.get("per_principal")
    if isinstance(per_principal, dict):
        for principal, pdata in per_principal.items():
            if not isinstance(principal, str) or not isinstance(pdata, dict):
                continue
            item_metrics: dict[str, float] = {}
            for key in ("actions", "errors", "llm_calls", "final_scrip"):
                value = pdata.get(key)
                if isinstance(value, (int, float)):
                    item_metrics[key] = float(value)
            log_item(
                run_id=run_id,
                item_id=principal,
                metrics=item_metrics,
                extra={"principal": principal},
                trace_id=trace_id,
            )

    return finish_run(
        run_id=run_id,
        summary_metrics=metrics,
        status="completed",
    )


def _list_experiments(
    *,
    llm_client_repo: str | None,
    dataset: str | None,
    project: str | None,
    limit: int,
) -> dict[str, Any]:
    _ensure_llm_client_import(llm_client_repo)
    from llm_client import get_runs

    runs = get_runs(dataset=dataset, project=project, limit=limit)
    return {"runs": runs}


def _detail_experiment(*, llm_client_repo: str | None, run_id: str) -> dict[str, Any]:
    _ensure_llm_client_import(llm_client_repo)
    from llm_client import get_run, get_run_items

    return {
        "run": get_run(run_id),
        "items": get_run_items(run_id),
    }


def _compare_experiments(*, llm_client_repo: str | None, run_ids: list[str]) -> dict[str, Any]:
    _ensure_llm_client_import(llm_client_repo)
    from llm_client import compare_runs

    return compare_runs(run_ids)


def _analyze_experiments(*, llm_client_repo: str | None, experiment_log: str | None) -> dict[str, Any]:
    _ensure_llm_client_import(llm_client_repo)
    from llm_client import analyze_history

    report = analyze_history(experiment_log=experiment_log)
    if hasattr(report, "model_dump"):
        return report.model_dump()
    if hasattr(report, "dict"):
        return report.dict()
    return {"report": str(report)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate emergence metrics from AE3 event logs.")
    parser.add_argument(
        "--events",
        default="logs/latest/events.jsonl",
        help="Path to events.jsonl, or logs dir when --run-id is provided.",
    )
    parser.add_argument("--run-id", default=None, help="Run id under logs dir (e.g., run_20260220_183640).")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")

    parser.add_argument("--log-experiment", action="store_true", help="Log summary into llm_client experiment registry.")
    parser.add_argument("--experiment-dataset", default="agent_ecology3_emergence", help="Experiment dataset label.")
    parser.add_argument("--experiment-project", default="agent_ecology3", help="Experiment project label.")
    parser.add_argument("--experiment-model", default=None, help="Override experiment model label.")
    parser.add_argument("--experiment-run-id", default=None, help="Optional explicit llm_client experiment run id.")
    parser.add_argument(
        "--llm-client-repo",
        default=os.environ.get("LLM_CLIENT_REPO", "/home/brian/projects/llm_client"),
        help="Path to llm_client repo for import fallback.",
    )

    parser.add_argument("--list-experiments", action="store_true", help="List llm_client experiment runs instead of summarizing events.")
    parser.add_argument("--experiment-limit", type=int, default=20, help="Limit for --list-experiments.")
    parser.add_argument("--detail-experiment", default=None, help="Show one experiment run + items by run id.")
    parser.add_argument("--compare-experiments", nargs="*", default=None, help="Compare 2+ experiment run ids.")
    parser.add_argument("--analyze-experiments", action="store_true", help="Run llm_client analyzer over experiment history.")
    parser.add_argument("--experiment-log-path", default=None, help="Optional experiments.jsonl path for analyzer.")

    args = parser.parse_args()

    payload: dict[str, Any]

    if args.list_experiments:
        payload = _list_experiments(
            llm_client_repo=args.llm_client_repo,
            dataset=args.experiment_dataset,
            project=args.experiment_project,
            limit=max(1, int(args.experiment_limit)),
        )
    elif args.detail_experiment:
        payload = _detail_experiment(
            llm_client_repo=args.llm_client_repo,
            run_id=args.detail_experiment,
        )
    elif args.compare_experiments:
        if len(args.compare_experiments) < 2:
            raise SystemExit("--compare-experiments requires at least two run ids")
        payload = _compare_experiments(
            llm_client_repo=args.llm_client_repo,
            run_ids=list(args.compare_experiments),
        )
    elif args.analyze_experiments:
        payload = _analyze_experiments(
            llm_client_repo=args.llm_client_repo,
            experiment_log=args.experiment_log_path,
        )
    else:
        events_path = _resolve_events_path(args.events, args.run_id)
        if not events_path.exists():
            raise SystemExit(f"events file not found: {events_path}")

        summary = summarize_events(events_path)
        payload = {"summary": summary}

        if args.log_experiment:
            finish_record = _log_summary_to_llm_client(
                summary=summary,
                events_path=events_path,
                ae3_run_id=args.run_id,
                dataset=args.experiment_dataset,
                project=args.experiment_project,
                model=args.experiment_model,
                llm_client_repo=args.llm_client_repo,
                experiment_run_id=args.experiment_run_id,
            )
            payload["experiment_run"] = finish_record

    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
