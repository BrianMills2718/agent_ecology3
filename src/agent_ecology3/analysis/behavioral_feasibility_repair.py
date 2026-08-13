"""Provider-free validation for the frozen Evaluation 14 design."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EVAL14_ACKNOWLEDGEMENTS = {
    "prescribed": "eval14/luna-medium/prescribed/pair-01/v1",
    "minimal": "eval14/luna-medium/minimal/pair-01/v1",
}


def validate_design(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the immutable, zero-provider Evaluation 14 contract."""
    boundary = payload.get("required_terminal_boundary")
    mint = payload.get("mint")
    distribution = payload.get("required_attempt_distribution")
    checks = {
        "identity": payload.get("evaluation_id") == "14_luna_behavioral_feasibility",
        "conditions": payload.get("conditions") == ["prescribed", "minimal"],
        "acknowledgements": payload.get("acknowledgements") == EVAL14_ACKNOWLEDGEMENTS,
        "single_new_seed": payload.get("matched_pairs")
        == [{"pair_id": "pair_01", "seed": 24140, "first_condition": "prescribed"}],
        "two_principals": payload.get("principal_count") == 2,
        "calibrated_budget": payload.get("starting_llm_budget_per_principal")
        == 0.033192,
        "balanced_fourteen_calls": payload.get(
            "required_committed_attempts_per_condition"
        )
        == 14
        and distribution == {"alpha_1": 7, "alpha_2": 7},
        "fifteenth_pre_dispatch_boundary": boundary
        == {
            "attempt_ordinal": 15,
            "phase": "pre_dispatch_rejected",
            "trace_id": None,
            "reason": "scarcity_binding_pre_dispatch",
        },
        "exact_call_ceiling": payload.get("maximum_provider_attempts") == 28,
        "no_retry_fallback_mcp": payload.get("provider_retries") == 0
        and payload.get("fallback_models") == []
        and payload.get("mcp_servers") == [],
        "fail_closed_actions": payload.get("local_action_failure_policy")
        == "fail_closed_no_substitute",
        "mint_without_scorer_calls": mint
        == {"enabled": True, "auction_after_horizon": True, "scoring_max_budget": 0.0},
        "narrow_decision": payload.get("decision")
        == "behavioral_instrument_feasibility_only",
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema_version": "ae3_eval14_preflight.v1",
        "status": "pass" if not failures else "blocked",
        "provider_calls": 0,
        "maximum_provider_attempts": 28,
        "checks": checks,
        "failed_checks": failures,
    }


def validate_design_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("evaluation design must be an object")
    return validate_design(payload)


def validate_cell_evidence(
    *,
    condition: str,
    checkpoint: dict[str, Any],
    status: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Validate a completed Eval 14 cell before its paired cell may start."""
    attempts = checkpoint.get("attempts")
    attempt_list = attempts if isinstance(attempts, list) else []
    committed = [
        item
        for item in attempt_list
        if isinstance(item, dict) and item.get("phase") == "committed"
    ]
    rejected = [
        item
        for item in attempt_list
        if isinstance(item, dict) and item.get("phase") == "pre_dispatch_rejected"
    ]
    distribution = {
        principal: sum(item.get("payer_id") == principal for item in committed)
        for principal in ("alpha_1", "alpha_2")
    }
    boundary = rejected[-1] if rejected else {}
    receipt_recovery = receipt.get("recovery")
    receipt_checkpoint = receipt.get("checkpoint")
    terminal_reason = checkpoint.get("terminal_reason")
    expected_ack = EVAL14_ACKNOWLEDGEMENTS.get(condition)
    shared_receipts = receipt.get("shared_client_receipts")
    mint = receipt.get("mint")
    checks = {
        "condition": condition in EVAL14_ACKNOWLEDGEMENTS,
        "acknowledgement": receipt.get("acknowledgement") == expected_ack,
        "fourteen_committed": len(committed) == 14,
        "balanced_distribution": distribution == {"alpha_1": 7, "alpha_2": 7},
        "fifteenth_boundary": len(attempt_list) == 15
        and len(rejected) == 1
        and boundary.get("ordinal") == 15
        and boundary.get("trace_id") is None,
        "dispatch_ceiling": checkpoint.get("provider_dispatch_count") == 14,
        "fail_closed_actions": receipt.get("local_action_failure_policy")
        == "fail_closed_no_substitute",
        "mint_without_scorer_calls": isinstance(mint, dict)
        and mint.get("enabled") is True
        and mint.get("scoring_max_budget") == 0.0
        and isinstance(mint.get("first_auction_delay_seconds"), (int, float))
        and mint["first_auction_delay_seconds"] > 3600,
        "terminal_reason": terminal_reason == "scarcity_binding_pre_dispatch",
        "terminal_equality": status.get("lifecycle_state") == "stopped"
        and status.get("terminal_reason") == terminal_reason
        and isinstance(receipt_recovery, dict)
        and receipt_recovery.get("lifecycle_state") == "stopped"
        and receipt_recovery.get("terminal_reason") == terminal_reason
        and isinstance(receipt_checkpoint, dict)
        and receipt_checkpoint.get("terminal_reason") == terminal_reason,
        "receipt_custody": isinstance(shared_receipts, list)
        and len(shared_receipts) == 14
        and all(
            isinstance(item, dict) and "receipt_error" not in item
            for item in shared_receipts
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema_version": "ae3_eval14_cell_validation.v1",
        "condition": condition,
        "status": "valid" if not failures else "invalid",
        "provider_dispatch_count": checkpoint.get("provider_dispatch_count"),
        "attempt_distribution": distribution,
        "checks": checks,
        "failed_checks": failures,
    }


def validate_cell_files(*, condition: str, data_dir: Path) -> dict[str, Any]:
    """Load and validate the three durable cell evidence surfaces."""
    payloads: dict[str, dict[str, Any]] = {}
    for name, filename in (
        ("checkpoint", "checkpoint.json"),
        ("status", "status.json"),
        ("receipt", "run_receipt.json"),
    ):
        payload = json.loads((data_dir / filename).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError(f"{filename} must contain an object")
        payloads[name] = payload
    return validate_cell_evidence(condition=condition, **payloads)
