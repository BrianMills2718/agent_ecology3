"""Compute emergence metrics from AE3 event logs and optionally log to llm_client experiments."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LLM_CLIENT_REPO = os.environ.get("LLM_CLIENT_REPO", str(PROJECT_ROOT.parent / "llm_client"))

_ARTIFACT_OWNER_PREFIX = re.compile(r"^(alpha_\d+)_")


def _load_llm_client_module() -> Any:
    """Load llm_client lazily so runtime path injection works without static stubs."""
    module: Any = importlib.import_module("llm_client")
    return module


def _coerce_dict_payload(payload: object, *, context: str) -> dict[str, Any]:
    """Normalize llm_client payloads to plain dicts and fail loudly on shape drift."""
    if isinstance(payload, dict):
        return payload

    model_dump = getattr(payload, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped

    as_dict = getattr(payload, "dict", None)
    if callable(as_dict):
        dumped = as_dict()
        if isinstance(dumped, dict):
            return dumped

    raise TypeError(f"{context} returned non-dict payload")


def _infer_owner(artifact_id: str, owner_map: dict[str, str]) -> str | None:
    owner = owner_map.get(artifact_id)
    if owner:
        return owner
    match = _ARTIFACT_OWNER_PREFIX.match(artifact_id)
    if match:
        return match.group(1)
    return None


def _derive_decision_origin_from_event(event: dict[str, Any]) -> str:
    origin = event.get("decision_origin")
    if isinstance(origin, str) and origin:
        return origin

    recovery_fallback_used = bool(event.get("recovery_fallback_used", False))
    if recovery_fallback_used:
        return "recovery"

    forced_explore = bool(event.get("forced_explore", False))
    if forced_explore:
        return "forced_explore"

    gate_fallback_used = bool(event.get("gate_fallback_used", False))
    llm_attempted = bool(event.get("llm_attempted", False))
    llm_success = bool(event.get("llm_success", False))
    if gate_fallback_used:
        return "llm_invalid_fallback" if llm_attempted else "fallback_without_llm"
    if llm_attempted and llm_success:
        return "llm_valid"
    if llm_attempted and not llm_success:
        return "llm_invalid_fallback"
    return "fallback_without_llm"


def summarize_events(path: Path) -> dict[str, Any]:
    event_types: Counter[str] = Counter()
    action_types: Counter[str] = Counter()
    loop_action_types: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    query_types: Counter[str] = Counter()
    transfer_edges: Counter[tuple[str, str]] = Counter()
    resource_transfer_edges: defaultdict[tuple[str, str, str], float] = defaultdict(float)
    read_edges: Counter[tuple[str, str]] = Counter()
    paid_consumption_edges: defaultdict[tuple[str, str], float] = defaultdict(float)
    paid_consumption_edge_events: Counter[tuple[str, str]] = Counter()
    artifact_cross_paid_revenue: defaultdict[str, float] = defaultdict(float)
    artifact_consumers: dict[str, set[str]] = {}
    revenue_by_principal_artifact_type: dict[str, defaultdict[str, float]] = {}
    value_by_decision_origin: defaultdict[str, float] = defaultdict(float)
    forced_explore_reason_counts: Counter[str] = Counter()
    decision_origin_counts: Counter[str] = Counter()
    per_principal_decision_origin_counts: dict[str, Counter[str]] = {}

    final_scrip: dict[str, int] = {}
    owner_map: dict[str, str] = {}
    artifact_creator: dict[str, str] = {}
    artifact_type_map: dict[str, str] = {}
    artifact_creation_origin: dict[str, str] = {}
    latest_loop_origin_by_principal: dict[str, str] = {}

    per_principal_actions: Counter[str] = Counter()
    per_principal_errors: Counter[str] = Counter()
    per_principal_llm_calls: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()
    per_principal_loop_decisions: Counter[str] = Counter()
    per_principal_loop_fallbacks: Counter[str] = Counter()
    per_principal_loop_successes: Counter[str] = Counter()
    per_principal_loop_errors: Counter[str] = Counter()
    per_principal_loop_repeat_errors: Counter[str] = Counter()
    last_loop_error_by_principal: dict[str, str] = {}
    minted_artifacts: set[str] = set()

    first_ts: str | None = None
    last_ts: str | None = None

    llm_calls = 0
    llm_call_errors = 0
    llm_cost = 0.0
    writes = 0
    reads_success = 0
    transfers = 0
    resource_transfers_total = 0
    llm_budget_transfer_amount = 0.0
    mint_submissions = 0
    kernel_queries_success = 0
    loop_decisions_total = 0
    loop_fallbacks_total = 0
    gate_fallbacks_total = 0
    recovery_fallbacks_total = 0
    forced_explore_total = 0
    loop_success_total = 0
    loop_error_total = 0
    loop_repeat_error_total = 0
    llm_attempted_total = 0
    llm_success_total = 0
    llm_valid_decision_total = 0

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

            if event_type == "llm_syscall_error":
                llm_call_errors += 1
                continue

            if event_type == "artifact_written":
                writes += 1
                artifact_id = event.get("artifact_id")
                owner = event.get("owner")
                writer = event.get("principal_id")
                artifact_type = event.get("artifact_type")
                if isinstance(artifact_id, str):
                    if isinstance(owner, str):
                        owner_map[artifact_id] = owner
                    elif isinstance(writer, str):
                        owner_map.setdefault(artifact_id, writer)
                    if isinstance(writer, str):
                        artifact_creator.setdefault(artifact_id, writer)
                        creation_origin = latest_loop_origin_by_principal.get(writer)
                        if isinstance(creation_origin, str) and creation_origin:
                            artifact_creation_origin.setdefault(artifact_id, creation_origin)
                    if isinstance(artifact_type, str) and artifact_type:
                        artifact_type_map[artifact_id] = artifact_type
                continue

            if event_type == "artifact_read":
                reads_success += 1
                principal = event.get("principal_id")
                artifact_id = event.get("artifact_id")
                if isinstance(principal, str) and isinstance(artifact_id, str):
                    owner = _infer_owner(artifact_id, owner_map)
                    if owner:
                        read_edges[(principal, owner)] += 1
                    recipient = event.get("recipient")
                    read_price_paid = float(event.get("read_price_paid") or 0.0)
                    if isinstance(recipient, str) and recipient and principal != recipient and read_price_paid > 0:
                        paid_consumption_edges[(principal, recipient)] += read_price_paid
                        paid_consumption_edge_events[(principal, recipient)] += 1
                        artifact_cross_paid_revenue[artifact_id] += read_price_paid
                        artifact_consumers.setdefault(artifact_id, set()).add(principal)
                        artifact_type = artifact_type_map.get(artifact_id, "unknown")
                        seller_revenue = revenue_by_principal_artifact_type.setdefault(recipient, defaultdict(float))
                        seller_revenue[artifact_type] += read_price_paid
                        origin = artifact_creation_origin.get(artifact_id, "unknown")
                        value_by_decision_origin[origin] += read_price_paid
                continue

            if event_type == "transfer":
                transfers += 1
                sender = event.get("sender")
                recipient = event.get("recipient")
                amount = int(event.get("amount") or 0)
                if isinstance(sender, str) and isinstance(recipient, str):
                    transfer_edges[(sender, recipient)] += amount
                continue

            if event_type == "resource_transfer":
                resource_transfers_total += 1
                sender = event.get("sender")
                recipient = event.get("recipient")
                resource = event.get("resource")
                resource_amount = float(event.get("amount") or 0.0)
                if isinstance(sender, str) and isinstance(recipient, str) and isinstance(resource, str):
                    resource_transfer_edges[(resource, sender, recipient)] += resource_amount
                    if resource == "llm_budget":
                        llm_budget_transfer_amount += resource_amount
                continue

            if event_type == "mint_submission":
                mint_submissions += 1
                continue

            if event_type == "mint_auction":
                artifact_id = event.get("artifact_id")
                if isinstance(artifact_id, str) and artifact_id:
                    minted_artifacts.add(artifact_id)
                continue

            if event_type == "kernel_query":
                kernel_queries_success += 1
                continue

            if event_type == "loop_decision":
                loop_decisions_total += 1
                principal = event.get("principal_id")
                if isinstance(principal, str):
                    per_principal_loop_decisions[principal] += 1
                    per_principal_decision_origin_counts.setdefault(principal, Counter())
                decision_action = event.get("decision_action")
                if isinstance(decision_action, str) and decision_action:
                    loop_action_types[decision_action] += 1

                gate_fallback_used = bool(event.get("gate_fallback_used"))
                recovery_fallback_used = bool(event.get("recovery_fallback_used"))
                fallback_used = bool(event.get("fallback_used")) or gate_fallback_used or recovery_fallback_used
                if fallback_used:
                    loop_fallbacks_total += 1
                    if isinstance(principal, str):
                        per_principal_loop_fallbacks[principal] += 1
                if gate_fallback_used:
                    gate_fallbacks_total += 1
                if recovery_fallback_used:
                    recovery_fallbacks_total += 1

                forced_explore = bool(event.get("forced_explore"))
                if forced_explore:
                    forced_explore_total += 1
                    forced_reason = event.get("forced_explore_reason")
                    if isinstance(forced_reason, str) and forced_reason:
                        forced_explore_reason_counts[forced_reason] += 1
                    else:
                        forced_explore_reason_counts["unspecified"] += 1

                decision_origin = _derive_decision_origin_from_event(event)
                decision_origin_counts[decision_origin] += 1
                if decision_origin == "llm_valid":
                    llm_valid_decision_total += 1
                if isinstance(principal, str):
                    per_principal_decision_origin_counts[principal][decision_origin] += 1
                    latest_loop_origin_by_principal[principal] = decision_origin

                llm_attempted = bool(event.get("llm_attempted", False))
                llm_success = bool(event.get("llm_success", False))
                if llm_attempted:
                    llm_attempted_total += 1
                if llm_success:
                    llm_success_total += 1

                result_success = event.get("result_success")
                if isinstance(result_success, bool) and result_success:
                    loop_success_total += 1
                    if isinstance(principal, str):
                        per_principal_loop_successes[principal] += 1
                    if isinstance(principal, str):
                        last_loop_error_by_principal.pop(principal, None)
                else:
                    error_code = event.get("result_error_code")
                    if isinstance(error_code, str) and error_code:
                        loop_error_total += 1
                        if isinstance(principal, str):
                            per_principal_loop_errors[principal] += 1
                            previous_error = last_loop_error_by_principal.get(principal)
                            if previous_error == error_code:
                                loop_repeat_error_total += 1
                                per_principal_loop_repeat_errors[principal] += 1
                            last_loop_error_by_principal[principal] = error_code
                    elif isinstance(principal, str):
                        last_loop_error_by_principal.pop(principal, None)
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

            if (
                action_type == "invoke_artifact"
                and bool(result.get("success"))
                and isinstance(principal, str)
                and isinstance(intent.get("artifact_id"), str)
            ):
                result_data = result.get("data")
                if isinstance(result_data, dict):
                    recipient = result_data.get("recipient")
                    price_paid = float(result_data.get("price_paid") or 0.0)
                    artifact_id = str(intent.get("artifact_id"))
                    if isinstance(recipient, str) and recipient and principal != recipient and price_paid > 0:
                        paid_consumption_edges[(principal, recipient)] += price_paid
                        paid_consumption_edge_events[(principal, recipient)] += 1
                        artifact_cross_paid_revenue[artifact_id] += price_paid
                        artifact_consumers.setdefault(artifact_id, set()).add(principal)
                        artifact_type = artifact_type_map.get(artifact_id, "unknown")
                        seller_revenue = revenue_by_principal_artifact_type.setdefault(recipient, defaultdict(float))
                        seller_revenue[artifact_type] += price_paid
                        origin = artifact_creation_origin.get(artifact_id, "unknown")
                        value_by_decision_origin[origin] += price_paid

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

    loop_action_total = sum(loop_action_types.values())
    loop_entropy_bits = 0.0
    if loop_action_total > 0:
        for count in loop_action_types.values():
            p = count / loop_action_total
            loop_entropy_bits -= p * math.log(p, 2)

    paid_consumption_total = float(sum(paid_consumption_edges.values()))
    paid_consumption_events_total = int(sum(paid_consumption_edge_events.values()))
    reuse_weighted_artifact_values: dict[str, float] = {}
    reuse_weighted_artifact_value_total = 0.0
    for artifact_id, revenue in artifact_cross_paid_revenue.items():
        distinct_consumers = len(artifact_consumers.get(artifact_id, set()))
        weighted = float(revenue) * (1.0 + math.log1p(float(distinct_consumers)))
        reuse_weighted_artifact_values[artifact_id] = round(weighted, 6)
        reuse_weighted_artifact_value_total += weighted

    specialization_hhi_by_principal: dict[str, float] = {}
    revenue_by_artifact_type: dict[str, dict[str, float]] = {}
    for principal, revenue_counter in revenue_by_principal_artifact_type.items():
        total_revenue = float(sum(revenue_counter.values()))
        if total_revenue <= 0:
            continue
        revenue_by_artifact_type[principal] = {atype: round(float(value), 6) for atype, value in sorted(revenue_counter.items())}
        hhi = 0.0
        for value in revenue_counter.values():
            share = float(value) / total_revenue
            hhi += share * share
        specialization_hhi_by_principal[principal] = round(hhi, 6)
    specialization_hhi_mean = (
        round(statistics.fmean(specialization_hhi_by_principal.values()), 6) if specialization_hhi_by_principal else 0.0
    )

    minted_artifact_count = len(minted_artifacts)
    minted_with_downstream_value_count = sum(1 for artifact_id in minted_artifacts if artifact_cross_paid_revenue.get(artifact_id, 0.0) > 0)
    mint_downstream_value = float(sum(artifact_cross_paid_revenue.get(artifact_id, 0.0) for artifact_id in minted_artifacts))
    mint_downstream_value_ratio = (
        round((minted_with_downstream_value_count / minted_artifact_count), 4) if minted_artifact_count > 0 else 0.0
    )

    forced_explore_value = float(value_by_decision_origin.get("forced_explore", 0.0))
    forced_explore_value_share = round((forced_explore_value / paid_consumption_total), 4) if paid_consumption_total > 0 else 0.0

    cross_read_events = sum(v for (src, dst), v in read_edges.items() if src != dst)
    cross_transfer_amount = sum(v for (src, dst), v in transfer_edges.items() if src != dst)
    cross_llm_budget_transfer_amount = sum(
        amount
        for (resource, src, dst), amount in resource_transfer_edges.items()
        if resource == "llm_budget" and src != dst
    )

    principals = sorted(set(final_scrip) | set(per_principal_actions) | set(per_principal_llm_calls))
    per_principal: dict[str, dict[str, int]] = {}
    for principal in principals:
        per_principal[principal] = {
            "actions": int(per_principal_actions.get(principal, 0)),
            "errors": int(per_principal_errors.get(principal, 0)),
            "llm_calls": int(per_principal_llm_calls.get(principal, 0)),
            "final_scrip": int(final_scrip.get(principal, 0)),
        }

    loop_principals = sorted(set(per_principal_loop_decisions) | set(per_principal))
    loop_decision_trends: dict[str, dict[str, float | int]] = {}
    for principal in loop_principals:
        decisions = int(per_principal_loop_decisions.get(principal, 0))
        fallbacks = int(per_principal_loop_fallbacks.get(principal, 0))
        successes = int(per_principal_loop_successes.get(principal, 0))
        errors_count = int(per_principal_loop_errors.get(principal, 0))
        repeat_errors = int(per_principal_loop_repeat_errors.get(principal, 0))
        loop_decision_trends[principal] = {
            "decisions": decisions,
            "fallbacks": fallbacks,
            "successes": successes,
            "errors": errors_count,
            "repeat_errors": repeat_errors,
            "fallback_rate": round((fallbacks / decisions), 4) if decisions > 0 else 0.0,
            "decision_success_rate": round((successes / decisions), 4) if decisions > 0 else 0.0,
            "repeat_error_rate": round((repeat_errors / errors_count), 4) if errors_count > 0 else 0.0,
        }

    decision_origin_share = {
        origin: round((count / loop_decisions_total), 4) if loop_decisions_total > 0 else 0.0
        for origin, count in sorted(decision_origin_counts.items())
    }
    decision_origin_trends: dict[str, dict[str, Any]] = {}
    for principal in loop_principals:
        decisions = int(per_principal_loop_decisions.get(principal, 0))
        per_origin = per_principal_decision_origin_counts.get(principal, Counter())
        decision_origin_trends[principal] = {
            "counts": {origin: int(count) for origin, count in sorted(per_origin.items())},
            "share": {
                origin: round((count / decisions), 4) if decisions > 0 else 0.0
                for origin, count in sorted(per_origin.items())
            },
        }

    dominant_model = model_counts.most_common(1)[0][0] if model_counts else "unknown"
    fallback_rate = round((loop_fallbacks_total / loop_decisions_total), 4) if loop_decisions_total > 0 else 0.0
    decision_success_rate = round((loop_success_total / loop_decisions_total), 4) if loop_decisions_total > 0 else 0.0
    repeat_error_rate = round((loop_repeat_error_total / loop_error_total), 4) if loop_error_total > 0 else 0.0
    gate_fallback_rate = round((gate_fallbacks_total / loop_decisions_total), 4) if loop_decisions_total > 0 else 0.0
    recovery_fallback_rate = round((recovery_fallbacks_total / loop_decisions_total), 4) if loop_decisions_total > 0 else 0.0
    forced_explore_rate = round((forced_explore_total / loop_decisions_total), 4) if loop_decisions_total > 0 else 0.0
    llm_attempt_rate = round((llm_attempted_total / loop_decisions_total), 4) if loop_decisions_total > 0 else 0.0
    llm_valid_decision_rate = round((llm_valid_decision_total / loop_decisions_total), 4) if loop_decisions_total > 0 else 0.0
    llm_attempt_success_rate = round((llm_success_total / llm_attempted_total), 4) if llm_attempted_total > 0 else 0.0
    llm_error_rate = round((llm_call_errors / (llm_calls + llm_call_errors)), 4) if (llm_calls + llm_call_errors) > 0 else 0.0

    return {
        "events_total": sum(event_types.values()),
        "event_types": dict(event_types),
        "actions_total": action_total,
        "action_types": dict(action_types),
        "action_entropy_bits": round(entropy_bits, 3),
        "loop_action_types": dict(loop_action_types),
        "loop_action_entropy_bits": round(loop_entropy_bits, 3),
        "llm_calls": llm_calls,
        "llm_call_errors": llm_call_errors,
        "llm_cost": round(llm_cost, 6),
        "writes": writes,
        "reads_success": reads_success,
        "transfers": transfers,
        "resource_transfers_total": resource_transfers_total,
        "llm_budget_transfer_amount": round(llm_budget_transfer_amount, 6),
        "cross_llm_budget_transfer_amount": round(cross_llm_budget_transfer_amount, 6),
        "mint_submissions": mint_submissions,
        "kernel_queries_success": kernel_queries_success,
        "loop_decisions_total": loop_decisions_total,
        "fallback_rate": fallback_rate,
        "gate_fallback_rate": gate_fallback_rate,
        "recovery_fallback_rate": recovery_fallback_rate,
        "forced_explore_rate": forced_explore_rate,
        "llm_attempted_total": llm_attempted_total,
        "llm_success_total": llm_success_total,
        "llm_valid_decision_total": llm_valid_decision_total,
        "llm_attempt_rate": llm_attempt_rate,
        "llm_valid_decision_rate": llm_valid_decision_rate,
        "llm_attempt_success_rate": llm_attempt_success_rate,
        "llm_error_rate": llm_error_rate,
        "decision_success_rate": decision_success_rate,
        "repeat_error_rate": repeat_error_rate,
        "decision_origin_counts": {origin: int(count) for origin, count in sorted(decision_origin_counts.items())},
        "decision_origin_share": decision_origin_share,
        "decision_origin_trends": decision_origin_trends,
        "forced_explore_reason_counts": {reason: int(count) for reason, count in sorted(forced_explore_reason_counts.items())},
        "loop_decision_trends": loop_decision_trends,
        "query_types": dict(query_types),
        "errors": dict(errors),
        "cross_read_events": cross_read_events,
        "cross_transfer_amount": cross_transfer_amount,
        "cross_paid_consumption_amount": round(paid_consumption_total, 6),
        "cross_paid_consumption_events": paid_consumption_events_total,
        "paid_consumption_edges": {
            f"{buyer}->{seller}": round(amount, 6) for (buyer, seller), amount in sorted(paid_consumption_edges.items())
        },
        "paid_consumption_edge_events": {
            f"{buyer}->{seller}": int(count) for (buyer, seller), count in sorted(paid_consumption_edge_events.items())
        },
        "artifact_cross_paid_revenue": {
            artifact_id: round(float(value), 6) for artifact_id, value in sorted(artifact_cross_paid_revenue.items())
        },
        "reuse_weighted_artifact_value_total": round(reuse_weighted_artifact_value_total, 6),
        "reuse_weighted_artifact_values": reuse_weighted_artifact_values,
        "revenue_by_artifact_type": revenue_by_artifact_type,
        "specialization_hhi_by_principal": specialization_hhi_by_principal,
        "specialization_hhi_mean": specialization_hhi_mean,
        "value_by_decision_origin": {
            origin: round(float(value), 6) for origin, value in sorted(value_by_decision_origin.items())
        },
        "forced_explore_value_share": forced_explore_value_share,
        "minted_artifact_count": minted_artifact_count,
        "minted_with_downstream_value_count": minted_with_downstream_value_count,
        "mint_downstream_value": round(mint_downstream_value, 6),
        "mint_downstream_value_ratio": mint_downstream_value_ratio,
        "transfer_edges": {
            f"{src}->{dst}": amount for (src, dst), amount in sorted(transfer_edges.items())
        },
        "resource_transfer_edges": {
            f"{resource}:{src}->{dst}": round(amount, 6)
            for (resource, src, dst), amount in sorted(resource_transfer_edges.items())
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
        "llm_call_errors",
        "llm_cost",
        "writes",
        "reads_success",
        "transfers",
        "resource_transfers_total",
        "llm_budget_transfer_amount",
        "cross_llm_budget_transfer_amount",
        "mint_submissions",
        "kernel_queries_success",
        "cross_read_events",
        "cross_transfer_amount",
        "loop_decisions_total",
        "fallback_rate",
        "gate_fallback_rate",
        "recovery_fallback_rate",
        "forced_explore_rate",
        "llm_attempted_total",
        "llm_success_total",
        "llm_valid_decision_total",
        "llm_attempt_rate",
        "llm_valid_decision_rate",
        "llm_attempt_success_rate",
        "llm_error_rate",
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
    condition_id: str | None = None,
    seed: int | None = None,
    replicate: int | None = None,
    scenario_id: str | None = None,
    phase: str | None = None,
) -> dict[str, Any]:
    _ensure_llm_client_import(llm_client_repo)
    llm_client = _load_llm_client_module()

    experiment_model = model or str(summary.get("dominant_model") or "unknown")
    metrics = _experiment_numeric_metrics(summary)
    metrics_schema = list(metrics.keys())

    config = {
        "source": "agent_ecology3",
        "ae3_run_id": ae3_run_id,
        "events_path": str(events_path),
        "condition_id": condition_id,
        "seed": seed,
        "replicate": replicate,
        "scenario_id": scenario_id,
        "phase": phase,
    }

    run_id = llm_client.start_run(
        dataset=dataset,
        model=experiment_model,
        config=config,
        condition_id=condition_id,
        seed=seed,
        replicate=replicate,
        scenario_id=scenario_id,
        phase=phase,
        metrics_schema=metrics_schema,
        run_id=experiment_run_id,
        project=project,
        provenance={
            "agent_ecology3_run": ae3_run_id,
            "events_file": str(events_path),
            "condition_id": condition_id,
            "seed": seed,
            "replicate": replicate,
            "scenario_id": scenario_id,
            "phase": phase,
        },
    )

    overall_extra = {
        "action_types": summary.get("action_types"),
        "errors": summary.get("errors"),
        "query_types": summary.get("query_types"),
        "model_counts": summary.get("model_counts"),
        "loop_decision_trends": summary.get("loop_decision_trends"),
    }
    trace_id = f"ae3/{ae3_run_id}" if ae3_run_id else None
    llm_client.log_item(
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
            llm_client.log_item(
                run_id=run_id,
                item_id=principal,
                metrics=item_metrics,
                extra={"principal": principal},
                trace_id=trace_id,
            )

    return _coerce_dict_payload(
        llm_client.finish_run(
            run_id=run_id,
            summary_metrics=metrics,
            status="completed",
        ),
        context="llm_client.finish_run",
    )


def _list_experiments(
    *,
    llm_client_repo: str | None,
    dataset: str | None,
    project: str | None,
    limit: int,
) -> dict[str, Any]:
    _ensure_llm_client_import(llm_client_repo)
    llm_client = _load_llm_client_module()
    runs = llm_client.get_runs(dataset=dataset, project=project, limit=limit)
    return {"runs": runs}


def _detail_experiment(*, llm_client_repo: str | None, run_id: str) -> dict[str, Any]:
    _ensure_llm_client_import(llm_client_repo)
    llm_client = _load_llm_client_module()

    return {
        "run": llm_client.get_run(run_id),
        "items": llm_client.get_run_items(run_id),
    }


def _compare_experiments(*, llm_client_repo: str | None, run_ids: list[str]) -> dict[str, Any]:
    _ensure_llm_client_import(llm_client_repo)
    llm_client = _load_llm_client_module()
    return _coerce_dict_payload(
        llm_client.compare_runs(run_ids),
        context="llm_client.compare_runs",
    )


def _analyze_experiments(*, llm_client_repo: str | None, experiment_log: str | None) -> dict[str, Any]:
    _ensure_llm_client_import(llm_client_repo)
    llm_client = _load_llm_client_module()
    report = llm_client.analyze_history(experiment_log=experiment_log)
    return _coerce_dict_payload(
        report,
        context="llm_client.analyze_history",
    )


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
        default=DEFAULT_LLM_CLIENT_REPO,
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
