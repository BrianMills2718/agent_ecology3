from __future__ import annotations

import pytest

from agent_ecology3.analysis.scarcity_calibration import build_calibration_readout


def test_readout_projects_candidates_from_largest_observed_charge() -> None:
    receipt = {
        "run_id": "plan10-poc",
        "attempts": [
            {"internal_estimated_budget_charge": 0.003873},
            {"internal_estimated_budget_charge": 0.004149},
        ],
    }

    readout = build_calibration_readout(
        receipt,
        existing_starting_budget=0.25,
        target_attempts_per_principal=16,
        principal_count=4,
    )

    assert readout["reference_charge"] == pytest.approx(0.004149)
    assert readout["existing_setting"] == {
        "starting_llm_budget": 0.25,
        "projected_attempt_capacity_per_principal": 60,
        "target_attempts_per_principal": 16,
        "projected_to_bind_within_horizon": False,
    }
    assert readout["candidate_settings"] == [
        {
            "label": "one_attempt_boundary",
            "projected_attempt_capacity_per_principal": 1,
            "starting_llm_budget": 0.004149,
            "total_llm_budget_stock": 0.016596,
        },
        {
            "label": "mid_horizon_candidate",
            "projected_attempt_capacity_per_principal": 8,
            "starting_llm_budget": 0.033192,
            "total_llm_budget_stock": 0.132768,
        },
        {
            "label": "full_horizon_control",
            "projected_attempt_capacity_per_principal": 16,
            "starting_llm_budget": 0.066384,
            "total_llm_budget_stock": 0.265536,
        },
    ]


@pytest.mark.parametrize(
    ("receipt", "error_type", "message"),
    [
        ({"attempts": []}, ValueError, "no positive"),
        (
            {"attempts": [{"internal_estimated_budget_charge": 0}]},
            ValueError,
            "no positive",
        ),
        ({}, TypeError, "must be a list"),
    ],
)
def test_readout_rejects_missing_charge_evidence(
    receipt: dict[str, object], error_type: type[Exception], message: str
) -> None:
    with pytest.raises(error_type, match=message):
        build_calibration_readout(
            receipt,
            existing_starting_budget=0.25,
            target_attempts_per_principal=16,
            principal_count=4,
        )


def test_readout_rejects_invalid_horizon() -> None:
    receipt = {"attempts": [{"internal_estimated_budget_charge": 0.004}]}
    with pytest.raises(ValueError, match="target_attempts_per_principal"):
        build_calibration_readout(
            receipt,
            existing_starting_budget=0.25,
            target_attempts_per_principal=1,
            principal_count=4,
        )
