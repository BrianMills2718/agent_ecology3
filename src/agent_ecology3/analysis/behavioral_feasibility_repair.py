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
