"""Configuration loading and strict validation for Agent Ecology 3."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Base model that rejects unknown keys."""

    model_config = ConfigDict(extra="forbid")


class LoopConfig(StrictModel):
    min_delay_seconds: float = 0.2
    max_delay_seconds: float = 8.0
    max_consecutive_errors: int = 5
    resource_check_interval_seconds: float = 1.0


class SimulationConfig(StrictModel):
    default_duration_seconds: float = 120.0
    max_runtime_seconds: float = 3600.0
    summary_interval_seconds: float = 15.0
    loop: LoopConfig = Field(default_factory=LoopConfig)


class PrincipalsConfig(StrictModel):
    count: int = 3
    id_prefix: str = "alpha_"
    starting_scrip: int = 100
    starting_llm_budget: float = 2.0
    starting_disk_quota_bytes: int = 250000


class RateLimitsConfig(StrictModel):
    llm_calls_per_window: float = 120.0
    llm_tokens_per_window: float = 200000.0
    cpu_seconds_per_window: float = 12.0


class StockResourcesConfig(StrictModel):
    total_llm_budget: float = 12.0
    total_disk_bytes: int = 1_000_000


class ResourcesConfig(StrictModel):
    rate_window_seconds: float = 60.0
    rate_limits: RateLimitsConfig = Field(default_factory=RateLimitsConfig)
    stock: StockResourcesConfig = Field(default_factory=StockResourcesConfig)


class LLMConfig(StrictModel):
    default_model: str = "minimax/minimax-m3"
    model_justification: str = "AE3 uses the configured allowlisted model for bounded agent-economy simulation."
    timeout_seconds: int = 60
    num_retries: int = Field(default=2, ge=0)
    max_output_tokens: int | None = Field(default=None, ge=1)
    provider_max_budget_usd: float = Field(default=0.0, ge=0.0)
    provider_budget_reservation_usd: float = Field(default=0.0, ge=0.0)
    allowed_models: list[str] = Field(default_factory=list)
    model_override_acceptance: dict[str, dict[str, str]] = Field(default_factory=dict)
    estimate_tokens_per_call: int = 900
    agent_cwd: str | None = None
    agent_max_turns: int | None = Field(default=6, ge=1)
    agent_permission_mode: str | None = None
    enable_bootstrap_loop_llm: bool = False
    loop_llm_cooldown_seconds: float = 0.0
    loop_forced_explore_mode: Literal["baseline", "reduced", "off"] = "off"
    loop_policy_seed: int = 0
    loop_cognition_mode: Literal["prescribed", "minimal"] = "prescribed"
    loop_prompt_template_path: str | None = None
    loop_prompt_feedback_enabled: bool = True
    # Artifacts listed in each loop prompt; scale runs need more than 24 so
    # seeded task statements stay visible (Plan 25).
    loop_snapshot_artifact_limit: int = Field(default=24, ge=1, le=500)
    loop_action_gate_enabled: bool = True
    loop_action_failure_policy: Literal[
        "recovery_fallback", "fail_closed_no_substitute"
    ] = "recovery_fallback"
    subscription_budget_charge_mode: Literal["actual", "estimated", "none"] = "estimated"
    subscription_estimated_cost_multiplier: float = Field(default=1.0, ge=0.0)
    decision_output_mode: Literal["legacy", "luna_structured_v1"] = "legacy"
    reasoning_effort: Literal["low", "medium", "high"] | None = None
    codex_transport: Literal["sdk", "cli", "auto"] | None = None
    codex_sandbox_mode: (
        Literal["read-only", "workspace-write", "danger-full-access"] | None
    ) = None
    codex_approval_policy: (
        Literal["never", "on-request", "on-failure", "untrusted"] | None
    ) = None
    codex_isolate_home: bool = True
    structured_response_model: Literal["LunaLoopDecisionV1"] | None = None
    expected_billing_mode: Literal["api_metered", "subscription_included"] | None = None

    @model_validator(mode="after")
    def validate_luna_structured_profile(self) -> LLMConfig:
        """Reject any partial or weakened Plan 10 Luna route before dispatch."""

        if self.decision_output_mode != "luna_structured_v1":
            return self

        expected: dict[str, object] = {
            "default_model": "codex/gpt-5.6-luna",
            "codex_transport": "cli",
            "codex_sandbox_mode": "read-only",
            "codex_approval_policy": "never",
            "codex_isolate_home": True,
            "structured_response_model": "LunaLoopDecisionV1",
            "expected_billing_mode": "subscription_included",
            "num_retries": 0,
            "agent_cwd": None,
        }
        mismatches = [
            f"{field}={getattr(self, field)!r} (expected {value!r})"
            for field, value in expected.items()
            if getattr(self, field) != value
        ]
        # Plan 10 qualified medium; Plan 24 adds low (Brian, 2026-10-05).
        if self.reasoning_effort not in ("medium", "low"):
            mismatches.append(
                f"reasoning_effort={self.reasoning_effort!r} (expected 'medium' or 'low')"
            )
        if self.allowed_models and self.allowed_models != ["codex/gpt-5.6-luna"]:
            mismatches.append(
                "allowed_models must be empty or exactly ['codex/gpt-5.6-luna']"
            )
        if mismatches:
            raise ValueError(
                "luna_structured_v1 requires the exact Plan 10 profile: "
                + "; ".join(mismatches)
            )
        return self


class ContractsConfig(StrictModel):
    default_when_missing: str = "kernel_contract_freeware"
    default_for_new_artifact: str = "kernel_contract_freeware"


class MintConfig(StrictModel):
    enabled: bool = True
    minimum_bid: int = 1
    first_auction_delay_seconds: float = 20.0
    bidding_window_seconds: float = 30.0
    period_seconds: float = 60.0
    mint_ratio: int = 10
    scoring_max_budget: float = Field(default=0.25, ge=0.0)
    # auction: periodic second-price auction scored by the LLM grader stand-in.
    # task_bounty: each submission is scored at once by hidden benchmark tests
    # (Plan 24); only the first passing submission per task is paid.
    mode: Literal["auction", "task_bounty"] = "auction"
    task_bank_path: str | None = None
    checker_timeout_seconds: float = Field(default=10.0, gt=0.0)
    # Paid to a helper's author when another agent's passing solution relies
    # on that helper's linked code (CodeFlowBench chains).
    royalty_scrip: int = Field(default=3, ge=0)

    @model_validator(mode="after")
    def validate_task_bounty(self) -> MintConfig:
        if self.mode == "task_bounty" and not self.task_bank_path:
            raise ValueError("mint.mode=task_bounty requires mint.task_bank_path")
        return self


class EconomyConfig(StrictModel):
    # False closes trading between principals: reading another principal's
    # artifacts and transferring to another principal are refused.
    cross_principal_trading: bool = True


class DashboardConfig(StrictModel):
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 9000
    jsonl_file: str = "logs/latest/events.jsonl"
    poll_interval_seconds: float = 1.0


class LoggingConfig(StrictModel):
    logs_dir: str = "logs"
    event_file_name: str = "events.jsonl"
    summary_file_name: str = "summary.jsonl"
    recent_event_limit: int = 500


class AppConfig(StrictModel):
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    principals: PrincipalsConfig = Field(default_factory=PrincipalsConfig)
    resources: ResourcesConfig = Field(default_factory=ResourcesConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    contracts: ContractsConfig = Field(default_factory=ContractsConfig)
    mint: MintConfig = Field(default_factory=MintConfig)
    economy: EconomyConfig = Field(default_factory=EconomyConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(config_path: str | Path = "config/config.yaml") -> AppConfig:
    """Load and strictly validate YAML config."""
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}
    return AppConfig.model_validate(raw)


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Load default config once and cache it."""
    return load_config()
