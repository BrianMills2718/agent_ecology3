"""Tests for mint artifact scoring through shared llm_client."""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Any

from agent_ecology3.world.mint import MintScorer


@dataclass
class _FakeLLMResult:
    """Small stand-in for llm_client's result object."""

    cost: float


def test_mint_scorer_uses_llm_client_structured_output(monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []

    def fake_call_llm_structured(**kwargs: Any) -> tuple[Any, _FakeLLMResult]:
        calls.append(kwargs)
        response_model = kwargs["response_model"]
        return response_model(score=87, reason="useful runnable artifact"), _FakeLLMResult(cost=0.0123)

    fake_module = types.ModuleType("llm_client")
    setattr(fake_module, "call_llm_structured", fake_call_llm_structured)
    monkeypatch.setitem(sys.modules, "llm_client", fake_module)

    scorer = MintScorer(model="minimax/minimax-m3", timeout_seconds=60, max_budget=0.07)
    score, reason = scorer.score_artifact(
        artifact_id="artifact_1",
        artifact_type="tool",
        content="does useful work",
        code="def run():\n    return 'ok'\n",
    )

    assert score == 87
    assert reason == "useful runnable artifact"
    assert scorer.last_cost == 0.0123
    assert scorer.last_error is None
    assert len(calls) == 1
    call = calls[0]
    assert call["model"] == "minimax/minimax-m3"
    assert call["task"] == "agent_ecology3_mint_scoring"
    assert call["trace_id"].startswith("agent_ecology3.mint_score.artifact_1.")
    assert call["max_budget"] == 0.07
    assert call["num_retries"] == 1
    assert call["messages"][0]["role"] == "user"
    assert "Return a structured score and reason." in call["messages"][0]["content"]


def test_mint_scorer_fallback_reports_llm_failure(monkeypatch: Any) -> None:
    def fake_call_llm_structured(**_: Any) -> tuple[Any, _FakeLLMResult]:
        raise RuntimeError("provider unavailable")

    fake_module = types.ModuleType("llm_client")
    setattr(fake_module, "call_llm_structured", fake_call_llm_structured)
    monkeypatch.setitem(sys.modules, "llm_client", fake_module)

    scorer = MintScorer(model="minimax/minimax-m3", timeout_seconds=60, max_budget=0.07)
    score, reason = scorer.score_artifact(
        artifact_id="artifact_2",
        artifact_type="tool",
        content="short content",
        code="def run():\n    return 'ok'\n",
    )

    assert score == 30
    assert "fallback score based on artifact complexity after LLM failure" in reason
    assert "RuntimeError: provider unavailable" in reason
    assert scorer.last_cost == 0.0
    assert scorer.last_error == "RuntimeError: provider unavailable"
