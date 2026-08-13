from __future__ import annotations

import pytest

from agent_ecology3.analysis.scarcity_calibration import (
    build_calibration_readout,
    build_control_comparison_readout,
)


def _midpoint_evidence() -> dict[str, object]:
    return {
        "status": "pass",
        "route": {
            "model": "codex/gpt-5.6-luna",
            "reasoning_effort": "medium",
            "transport": "cli",
            "mcp_servers": [],
            "retry_count": 0,
            "fallback_models": [],
        },
        "source": {"llm_client_revision": "accepted-client"},
        "frozen_setting": {"starting_llm_budget": 0.033192},
        "readout": {
            "terminal_reason": "scarcity_binding_pre_dispatch",
            "boundary_attempt_phase": "pre_dispatch_rejected",
            "boundary_trace_id": None,
            "provider_dispatch_count": 7,
        },
    }


def _control_receipt() -> dict[str, object]:
    return {
        "acknowledgement": "plan11/luna-medium/scarcity-control/v1",
        "model": "codex/gpt-5.6-luna",
        "reasoning_effort": "medium",
        "transport": "cli",
        "mcp_servers": [],
        "retry_count": 0,
        "fallback_models": [],
        "source": {"llm_client_revision": "accepted-client"},
        "starting_llm_budget": 0.066384,
        "recovery": {
            "lifecycle_state": "completed",
            "provider_dispatch_count": 8,
            "committed_attempts": 8,
            "terminal_reason": None,
        },
        "checkpoint": {
            "attempts": [
                {
                    "phase": "committed",
                    "trace_id": f"trace-{ordinal}",
                    "syscall_result": {
                        "structured_action": {"action_type": "query_kernel"}
                    },
                }
                for ordinal in range(1, 9)
            ]
        },
    }


def test_control_comparison_requires_midpoint_binding_and_control_completion() -> None:
    readout = build_control_comparison_readout(
        _midpoint_evidence(), _control_receipt()
    )
    assert readout["status"] == "pass"
    assert readout["decision"] == "manipulation_separates_within_eight_attempt_horizon"
    assert readout["midpoint"]["scarcity_binding"] is True
    assert readout["control"]["completed_horizon"] is True
    assert len(readout["control"]["action_types"]) == 8


@pytest.mark.parametrize(
    "mutation",
    (
        "control_bound",
        "control_short",
        "midpoint_not_bound",
        "control_wrong_budget",
        "route_mismatch",
    ),
)
def test_control_comparison_invalidates_failed_separation(mutation: str) -> None:
    midpoint = _midpoint_evidence()
    control = _control_receipt()
    if mutation == "control_bound":
        control["recovery"]["lifecycle_state"] = "stopped"  # type: ignore[index]
        control["recovery"]["terminal_reason"] = "scarcity_binding_pre_dispatch"  # type: ignore[index]
    elif mutation == "control_short":
        control["recovery"]["provider_dispatch_count"] = 7  # type: ignore[index]
    elif mutation == "midpoint_not_bound":
        midpoint["readout"]["terminal_reason"] = None  # type: ignore[index]
    elif mutation == "control_wrong_budget":
        control["starting_llm_budget"] = 0.25
    else:
        control["model"] = "different/model"
    assert build_control_comparison_readout(midpoint, control)["status"] == "invalid"


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
