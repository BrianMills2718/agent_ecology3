from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from agent_ecology3.analysis.behavioral_feasibility import (
    validate_design,
    validate_design_file,
)

DESIGN = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "evaluations"
    / "12_luna_behavioral_feasibility.json"
)


def test_canonical_design_passes_without_provider_calls() -> None:
    result = validate_design_file(DESIGN)
    assert result["status"] == "pass"
    assert result["provider_calls"] == 0
    assert result["maximum_provider_attempts"] == 32
    assert all(result["checks"].values())


@pytest.mark.parametrize(
    ("field", "value", "failed_check"),
    [
        ("maximum_provider_attempts", 33, "exact_call_ceiling"),
        ("provider_retries", 1, "no_retry_fallback_mcp"),
        ("starting_llm_budget_per_principal", 0.25, "calibrated_budget"),
        ("principal_count", 1, "two_principals"),
        ("decision", "causal_effect", "narrow_decision"),
    ],
)
def test_design_mutations_fail_closed(
    field: str, value: object, failed_check: str
) -> None:
    payload = json.loads(DESIGN.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated[field] = value
    result = validate_design(mutated)
    assert result["status"] == "blocked"
    assert failed_check in result["failed_checks"]
