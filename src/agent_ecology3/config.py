"""Configuration loading and strict validation for Agent Ecology 3."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


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
    default_model: str = "gemini/gemini-2.5-flash"
    timeout_seconds: int = 60
    allowed_models: list[str] = Field(default_factory=list)
    estimate_tokens_per_call: int = 900
    enable_bootstrap_loop_llm: bool = False


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
