"""Scenario tests for the strict-config capability (openspec/specs/strict-config)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_ecology3.config import AppConfig, LLMConfig, MintConfig


@pytest.mark.req("strict-config/unknown-key", existing=True)
def test_unknown_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AppConfig.model_validate({"unknown_block": {"should_fail": True}})


@pytest.mark.req("strict-config/known-keys-only", existing=True)
def test_known_keys_only_validates() -> None:
    cfg = AppConfig.model_validate({"principals": {"count": 2}})
    assert cfg.principals.count == 2


@pytest.mark.req("strict-config/task-bounty-without-a-task-bank", existing=True)
def test_task_bounty_requires_task_bank_path() -> None:
    with pytest.raises(ValidationError, match="task_bank_path"):
        MintConfig.model_validate({"mode": "task_bounty"})


@pytest.mark.req("strict-config/partial-luna-profile", existing=True)
def test_partial_luna_profile_is_rejected() -> None:
    with pytest.raises(ValidationError, match="default_model"):
        LLMConfig.model_validate({"decision_output_mode": "luna_structured_v1"})
