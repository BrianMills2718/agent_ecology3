"""Provider-free validation for the frozen Evaluation 12 design."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def validate_design(payload: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    pairs = payload.get("matched_pairs")
    conditions = payload.get("conditions")
    attempts = payload.get("provider_attempts_per_condition")
    expected_max = (
        len(pairs) * len(conditions) * attempts
        if isinstance(pairs, list)
        and isinstance(conditions, list)
        and isinstance(attempts, int)
        else None
    )
    checks = {
        "identity": payload.get("evaluation_id") == "12_luna_behavioral_feasibility",
        "single_matched_pair": isinstance(pairs, list) and len(pairs) == 1,
        "conditions": conditions == ["prescribed", "minimal"],
        "two_principals": payload.get("principal_count") == 2,
        "calibrated_budget": payload.get("starting_llm_budget_per_principal")
        == 0.033192,
        "sixteen_attempt_horizon": attempts == 16,
        "exact_call_ceiling": payload.get("maximum_provider_attempts")
        == expected_max
        == 32,
        "luna_route": payload.get("model") == "codex/gpt-5.6-luna"
        and payload.get("reasoning_effort") == "medium",
        "no_retry_fallback_mcp": payload.get("provider_retries") == 0
        and payload.get("fallback_models") == []
        and payload.get("mcp_servers") == [],
        "narrow_decision": payload.get("decision")
        == "behavioral_instrument_feasibility_only",
    }
    failures.extend(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "ae3_eval12_preflight.v1",
        "status": "pass" if not failures else "blocked",
        "provider_calls": 0,
        "maximum_provider_attempts": expected_max,
        "checks": checks,
        "failed_checks": failures,
    }


def validate_design_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("evaluation design must be an object")
    return validate_design(payload)
