"""Provider-free scarcity calibration from retained Luna settlement receipts."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _positive_charges(receipt: dict[str, Any]) -> list[float]:
    attempts = receipt.get("attempts")
    if not isinstance(attempts, list):
        raise TypeError("receipt.attempts must be a list")
    charges: list[float] = []
    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue
        value = attempt.get("internal_estimated_budget_charge")
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            charges.append(float(value))
    if not charges:
        raise ValueError("receipt contains no positive internal estimated budget charges")
    return charges


def build_calibration_readout(
    receipt: dict[str, Any],
    *,
    existing_starting_budget: float,
    target_attempts_per_principal: int,
    principal_count: int,
) -> dict[str, Any]:
    """Project candidate budgets without claiming that future behavior will bind."""
    if existing_starting_budget < 0:
        raise ValueError("existing_starting_budget must be >= 0")
    if target_attempts_per_principal < 2:
        raise ValueError("target_attempts_per_principal must be >= 2")
    if principal_count < 1:
        raise ValueError("principal_count must be >= 1")

    charges = _positive_charges(receipt)
    reference_charge = max(charges)
    projected_capacity = math.floor(existing_starting_budget / reference_charge)
    midpoint = max(1, target_attempts_per_principal // 2)
    capacities = tuple(dict.fromkeys((1, midpoint, target_attempts_per_principal)))
    candidates = [
        {
            "label": (
                "one_attempt_boundary"
                if capacity == 1
                else "full_horizon_control"
                if capacity == target_attempts_per_principal
                else "mid_horizon_candidate"
            ),
            "projected_attempt_capacity_per_principal": capacity,
            "starting_llm_budget": round(reference_charge * capacity, 8),
            "total_llm_budget_stock": round(
                reference_charge * capacity * principal_count, 8
            ),
        }
        for capacity in capacities
    ]
    return {
        "schema_version": "ae3_scarcity_calibration_readout.v1",
        "status": "provider_free_projection",
        "source_run_id": receipt.get("run_id"),
        "observed_attempt_count": len(charges),
        "observed_internal_charges": charges,
        "reference_charge": reference_charge,
        "reference_rule": "maximum retained Plan 10 internal estimated charge",
        "existing_setting": {
            "starting_llm_budget": existing_starting_budget,
            "projected_attempt_capacity_per_principal": projected_capacity,
            "target_attempts_per_principal": target_attempts_per_principal,
            "projected_to_bind_within_horizon": projected_capacity
            < target_attempts_per_principal,
        },
        "candidate_settings": candidates,
        "next_authentic_probe": {
            "candidate": "mid_horizon_candidate",
            "readout": (
                "retained insufficient_budget receipt before the target horizon, "
                "with concrete action and budget trajectory visible"
            ),
            "disproof": (
                "the run reaches its target horizon without an insufficient_budget "
                "receipt, or a non-budget gate prevents interpreting scarcity"
            ),
        },
        "non_claims": [
            "Observed charges are references, not a bound on future prompt cost.",
            "Projected capacity does not establish behavioral scarcity binding.",
            "No provider call was made by this readout.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--existing-starting-budget", type=float, required=True)
    parser.add_argument("--target-attempts-per-principal", type=int, required=True)
    parser.add_argument("--principal-count", type=int, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    readout = build_calibration_readout(
        receipt,
        existing_starting_budget=args.existing_starting_budget,
        target_attempts_per_principal=args.target_attempts_per_principal,
        principal_count=args.principal_count,
    )
    rendered = json.dumps(readout, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
