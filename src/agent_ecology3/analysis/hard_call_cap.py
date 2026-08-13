"""Provider-free custody checks for Evaluation 15's hard call cap."""

from __future__ import annotations

from typing import Any

EVAL15_ACKNOWLEDGEMENTS = {
    "prescribed": "eval15/luna-medium/prescribed/pair-01/v1",
    "minimal": "eval15/luna-medium/minimal/pair-01/v1",
}


def validate_capped_cell(
    *,
    condition: str,
    checkpoint: dict[str, Any],
    status: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Require exactly fourteen committed calls and completed custody."""
    raw_attempts = checkpoint.get("attempts")
    attempts = raw_attempts if isinstance(raw_attempts, list) else []
    committed = [
        item
        for item in attempts
        if isinstance(item, dict) and item.get("phase") == "committed"
    ]
    distribution = {
        principal: sum(item.get("payer_id") == principal for item in committed)
        for principal in ("alpha_1", "alpha_2")
    }
    receipt_recovery = receipt.get("recovery")
    receipt_checkpoint = receipt.get("checkpoint")
    shared_receipts = receipt.get("shared_client_receipts")
    mint = receipt.get("mint")
    checks = {
        "acknowledgement": receipt.get("acknowledgement")
        == EVAL15_ACKNOWLEDGEMENTS.get(condition),
        "hard_fourteen_call_cap": len(attempts) == 14
        and len(committed) == 14
        and checkpoint.get("provider_dispatch_count") == 14,
        "balanced_distribution": distribution == {"alpha_1": 7, "alpha_2": 7},
        "completed_custody": checkpoint.get("terminal_state") is None
        and checkpoint.get("terminal_reason") is None
        and status.get("lifecycle_state") == "completed"
        and status.get("terminal_reason") is None
        and isinstance(receipt_recovery, dict)
        and receipt_recovery.get("lifecycle_state") == "completed"
        and isinstance(receipt_checkpoint, dict)
        and receipt_checkpoint.get("provider_dispatch_count") == 14,
        "receipt_custody": isinstance(shared_receipts, list)
        and len(shared_receipts) == 14
        and all(
            isinstance(item, dict) and "receipt_error" not in item
            for item in shared_receipts
        ),
        "fail_closed_actions": receipt.get("local_action_failure_policy")
        == "fail_closed_no_substitute",
        "mint_without_scorer_calls": isinstance(mint, dict)
        and mint.get("enabled") is True
        and mint.get("scoring_max_budget") == 0.0,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "schema_version": "ae3_eval15_cell_validation.v1",
        "condition": condition,
        "status": "valid" if not failures else "invalid",
        "provider_dispatch_count": checkpoint.get("provider_dispatch_count"),
        "attempt_distribution": distribution,
        "checks": checks,
        "failed_checks": failures,
    }
