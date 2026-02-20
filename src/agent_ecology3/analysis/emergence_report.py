"""Compute emergence metrics from AE3 event logs."""

from __future__ import annotations

import argparse
import json
import math
import re
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

            if event_type == "llm_syscall":
                llm_calls += 1
                llm_cost += float(event.get("charged_cost") or 0.0)
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

            if action_type == "query_kernel":
                query_type = intent.get("query_type")
                if isinstance(query_type, str):
                    query_types[query_type] += 1

            if not bool(result.get("success")):
                errors[str(result.get("error_code") or "unknown")] += 1

            principal = intent.get("principal_id")
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
    }


def _resolve_events_path(log_path: str, run_id: str | None) -> Path:
    if run_id:
        return Path(log_path) / run_id / "events.jsonl"
    return Path(log_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate emergence metrics from AE3 event logs.")
    parser.add_argument(
        "--events",
        default="logs/latest/events.jsonl",
        help="Path to events.jsonl, or logs dir when --run-id is provided.",
    )
    parser.add_argument("--run-id", default=None, help="Run id under logs dir (e.g., run_20260220_183640).")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()

    events_path = _resolve_events_path(args.events, args.run_id)
    if not events_path.exists():
        raise SystemExit(f"events file not found: {events_path}")

    summary = summarize_events(events_path)
    if args.pretty:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
