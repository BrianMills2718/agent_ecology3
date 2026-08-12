from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from agent_ecology3.cli import _load_runtime_config
from agent_ecology3.config import load_config
from agent_ecology3.world.actions import (
    QueryKernelIntent,
    TransferIntent,
    TransferResourceIntent,
    parse_intent_from_json,
)

model_override_acceptance = {
    "accepted_by": "brian",
    "reason": "Tests exercise explicit CLI override handling; MiniMax-M3 remains the baseline/default model.",
}


def test_config_rejects_unknown_keys(tmp_path) -> None:
    cfg = tmp_path / "bad.yaml"
    cfg.write_text(
        """
simulation:
  default_duration_seconds: 60
principals:
  count: 1
resources:
  rate_window_seconds: 60
  rate_limits:
    llm_calls_per_window: 10
    llm_tokens_per_window: 1000
    cpu_seconds_per_window: 5
  stock:
    total_llm_budget: 1.0
    total_disk_bytes: 10000
llm:
  default_model: minimax/minimax-m3
  timeout_seconds: 30
  allowed_models: []
  estimate_tokens_per_call: 500
  enable_bootstrap_loop_llm: false
contracts:
  default_when_missing: kernel_contract_freeware
  default_for_new_artifact: kernel_contract_freeware
mint:
  enabled: true
  minimum_bid: 1
  first_auction_delay_seconds: 20
  bidding_window_seconds: 30
  period_seconds: 60
  mint_ratio: 10
dashboard:
  enabled: false
  host: 0.0.0.0
  port: 9000
  jsonl_file: logs/latest/events.jsonl
  poll_interval_seconds: 1.0
logging:
  logs_dir: logs
  event_file_name: events.jsonl
  summary_file_name: summary.jsonl
  recent_event_limit: 100
unknown_block:
  should_fail: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_config(cfg)


def test_removed_actions_are_rejected() -> None:
    payload = {
        "action_type": "submit_to_task",
        "artifact_id": "x",
        "task_id": "y",
    }
    parsed = parse_intent_from_json("alpha_1", json.dumps(payload))
    assert isinstance(parsed, str)
    assert "Unknown action_type" in parsed

    payload = {
        "action_type": "configure_context",
        "sections": {"events": True},
    }
    parsed = parse_intent_from_json("alpha_1", json.dumps(payload))
    assert isinstance(parsed, str)
    assert "Unknown action_type" in parsed


def test_query_alias_payload_normalizes_from_action_and_parameters() -> None:
    payload = {
        "action_type": "noop",
        "action": "query_kernel",
        "parameters": {
            "query": "simulation status",
        },
    }
    parsed = parse_intent_from_json("alpha_1", json.dumps(payload))
    assert isinstance(parsed, QueryKernelIntent)
    assert parsed.query_type == "events"
    assert isinstance(parsed.params, dict)


def test_unknown_query_type_is_inferred_to_supported_query() -> None:
    payload = {
        "action_type": "query_kernel",
        "query_type": "read_artifact",
    }
    parsed = parse_intent_from_json("alpha_1", json.dumps(payload))
    assert isinstance(parsed, QueryKernelIntent)
    assert parsed.query_type == "artifacts"


def test_transfer_alias_coerces_numeric_amount() -> None:
    payload = {
        "action": "transfer",
        "parameters": {
            "recipient": "alpha_2",
            "amount": "3",
        },
    }
    parsed = parse_intent_from_json("alpha_1", json.dumps(payload))
    assert isinstance(parsed, TransferIntent)
    assert parsed.recipient_id == "alpha_2"
    assert parsed.amount == 3
    assert parsed.to_dict()["recipient_id"] == "alpha_2"


def test_transfer_resource_alias_coerces_float_amount() -> None:
    payload = {
        "action": "transfer_resource",
        "parameters": {
            "recipient": "alpha_2",
            "resource_name": "llm_budget",
            "amount": "0.25",
        },
    }
    parsed = parse_intent_from_json("alpha_1", json.dumps(payload))
    assert isinstance(parsed, TransferResourceIntent)
    assert parsed.recipient_id == "alpha_2"
    assert parsed.resource == "llm_budget"
    assert parsed.amount == 0.25


def test_non_object_payload_rejected() -> None:
    parsed = parse_intent_from_json("alpha_1", json.dumps(["not", "an", "action"]))
    assert parsed == "Action payload must be a JSON object"


def test_cli_loop_llm_cooldown_override_and_validation(tmp_path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
simulation:
  default_duration_seconds: 60
  max_runtime_seconds: 3600
  summary_interval_seconds: 10
  loop:
    min_delay_seconds: 0.1
    max_delay_seconds: 1.0
    max_consecutive_errors: 3
    resource_check_interval_seconds: 0.1
principals:
  count: 2
  id_prefix: alpha_
  starting_scrip: 100
  starting_llm_budget: 2.0
  starting_disk_quota_bytes: 100000
resources:
  rate_window_seconds: 60
  rate_limits:
    llm_calls_per_window: 10
    llm_tokens_per_window: 1000
    cpu_seconds_per_window: 5
  stock:
    total_llm_budget: 2.0
    total_disk_bytes: 1000000
llm:
  default_model: minimax/minimax-m3
  timeout_seconds: 30
  allowed_models: []
  estimate_tokens_per_call: 500
  enable_bootstrap_loop_llm: false
  loop_llm_cooldown_seconds: 3.0
  loop_prompt_feedback_enabled: true
  loop_action_gate_enabled: true
contracts:
  default_when_missing: kernel_contract_freeware
  default_for_new_artifact: kernel_contract_freeware
mint:
  enabled: true
  minimum_bid: 1
  first_auction_delay_seconds: 20
  bidding_window_seconds: 30
  period_seconds: 60
  mint_ratio: 10
dashboard:
  enabled: false
  host: 0.0.0.0
  port: 9000
  jsonl_file: logs/latest/events.jsonl
  poll_interval_seconds: 1.0
logging:
  logs_dir: logs
  event_file_name: events.jsonl
  summary_file_name: summary.jsonl
  recent_event_limit: 100
""",
        encoding="utf-8",
    )

    loaded = _load_runtime_config(
        str(cfg),
        agents_override=None,
        llm_loop_override="on",
        loop_llm_cooldown_override=1.5,
        loop_forced_explore_override="reduced",
        loop_policy_seed_override=17,
    )
    assert loaded.llm.enable_bootstrap_loop_llm is True
    assert loaded.llm.loop_llm_cooldown_seconds == 1.5
    assert loaded.llm.loop_forced_explore_mode == "reduced"
    assert loaded.llm.loop_policy_seed == 17

    loaded = _load_runtime_config(str(cfg), agents_override=None, llm_loop_override="off")
    assert loaded.llm.enable_bootstrap_loop_llm is False

    with pytest.raises(ValueError, match="--loop-llm-cooldown must be >= 0"):
        _load_runtime_config(str(cfg), agents_override=None, loop_llm_cooldown_override=-1.0)

    with pytest.raises(ValueError, match="--llm-loop must be one of: on, off"):
        _load_runtime_config(str(cfg), agents_override=None, llm_loop_override="maybe")

    with pytest.raises(ValueError, match="--loop-forced-explore must be one of: baseline, reduced, off"):
        _load_runtime_config(str(cfg), agents_override=None, loop_forced_explore_override="invalid")


def test_cli_loop_prompt_template_override_validation(tmp_path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
simulation:
  default_duration_seconds: 60
  max_runtime_seconds: 3600
  summary_interval_seconds: 10
  loop:
    min_delay_seconds: 0.1
    max_delay_seconds: 1.0
    max_consecutive_errors: 3
    resource_check_interval_seconds: 0.1
principals:
  count: 2
  id_prefix: alpha_
  starting_scrip: 100
  starting_llm_budget: 2.0
  starting_disk_quota_bytes: 100000
resources:
  rate_window_seconds: 60
  rate_limits:
    llm_calls_per_window: 10
    llm_tokens_per_window: 1000
    cpu_seconds_per_window: 5
  stock:
    total_llm_budget: 2.0
    total_disk_bytes: 1000000
llm:
  default_model: minimax/minimax-m3
  timeout_seconds: 30
  allowed_models: []
  estimate_tokens_per_call: 500
  enable_bootstrap_loop_llm: false
contracts:
  default_when_missing: kernel_contract_freeware
  default_for_new_artifact: kernel_contract_freeware
mint:
  enabled: true
  minimum_bid: 1
  first_auction_delay_seconds: 20
  bidding_window_seconds: 30
  period_seconds: 60
  mint_ratio: 10
dashboard:
  enabled: false
  host: 0.0.0.0
  port: 9000
  jsonl_file: logs/latest/events.jsonl
  poll_interval_seconds: 1.0
logging:
  logs_dir: logs
  event_file_name: events.jsonl
  summary_file_name: summary.jsonl
  recent_event_limit: 100
""",
        encoding="utf-8",
    )
    prompt_template = tmp_path / "loop_prompt.txt"
    prompt_template.write_text("Template for {principal_id}", encoding="utf-8")

    loaded = _load_runtime_config(
        str(cfg),
        agents_override=None,
        loop_prompt_template_override=str(prompt_template),
    )
    assert loaded.llm.loop_prompt_template_path == str(prompt_template)

    with pytest.raises(ValueError, match="--loop-prompt-template must be a non-empty string path"):
        _load_runtime_config(str(cfg), agents_override=None, loop_prompt_template_override="   ")


def test_cli_model_override_updates_default_and_allowed_models(tmp_path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
simulation:
  default_duration_seconds: 60
  max_runtime_seconds: 3600
  summary_interval_seconds: 10
  loop:
    min_delay_seconds: 0.1
    max_delay_seconds: 1.0
    max_consecutive_errors: 3
    resource_check_interval_seconds: 0.1
principals:
  count: 2
  id_prefix: alpha_
  starting_scrip: 100
  starting_llm_budget: 2.0
  starting_disk_quota_bytes: 100000
resources:
  rate_window_seconds: 60
  rate_limits:
    llm_calls_per_window: 10
    llm_tokens_per_window: 1000
    cpu_seconds_per_window: 5
  stock:
    total_llm_budget: 2.0
    total_disk_bytes: 1000000
llm:
  default_model: minimax/minimax-m3
  timeout_seconds: 30
  allowed_models:
    - minimax/minimax-m3
  estimate_tokens_per_call: 500
  enable_bootstrap_loop_llm: false
contracts:
  default_when_missing: kernel_contract_freeware
  default_for_new_artifact: kernel_contract_freeware
mint:
  enabled: true
  minimum_bid: 1
  first_auction_delay_seconds: 20
  bidding_window_seconds: 30
  period_seconds: 60
  mint_ratio: 10
dashboard:
  enabled: false
  host: 0.0.0.0
  port: 9000
  jsonl_file: logs/latest/events.jsonl
  poll_interval_seconds: 1.0
logging:
  logs_dir: logs
  event_file_name: events.jsonl
  summary_file_name: summary.jsonl
  recent_event_limit: 100
""",
        encoding="utf-8",
    )

    loaded = _load_runtime_config(str(cfg), agents_override=None, model_override="claude-code/opus")
    assert loaded.llm.default_model == "claude-code/opus"
    assert "claude-code/opus" in loaded.llm.allowed_models

    with pytest.raises(ValueError, match="--model must be a non-empty string"):
        _load_runtime_config(str(cfg), agents_override=None, model_override="   ")


def test_subscription_budget_config_fields_load(tmp_path) -> None:
    cfg = tmp_path / "subscription.yaml"
    cfg.write_text(
        """
llm:
  subscription_budget_charge_mode: none
  subscription_estimated_cost_multiplier: 0.75
""",
        encoding="utf-8",
    )

    loaded = load_config(cfg)
    assert loaded.llm.subscription_budget_charge_mode == "none"
    assert loaded.llm.subscription_estimated_cost_multiplier == pytest.approx(0.75)


def test_cognition_and_provider_budget_config_fields_load(tmp_path) -> None:
    cfg = tmp_path / "ablation.yaml"
    cfg.write_text(
        """
llm:
  loop_cognition_mode: minimal
  num_retries: 0
  max_output_tokens: 512
  provider_max_budget_usd: 0.25
  provider_budget_reservation_usd: 0.01
""",
        encoding="utf-8",
    )

    loaded = load_config(cfg)
    assert loaded.llm.loop_cognition_mode == "minimal"
    assert loaded.llm.num_retries == 0
    assert loaded.llm.max_output_tokens == 512
    assert loaded.llm.provider_max_budget_usd == pytest.approx(0.25)
    assert loaded.llm.provider_budget_reservation_usd == pytest.approx(0.01)
