"""Tests for mint artifact scoring through shared llm_client."""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Any

import pytest

from agent_ecology3.world.ledger import Ledger
from agent_ecology3.world.mint import MintAuction, MintScorer, MintScoringError
from agent_ecology3.world.rates import RateTracker


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


def test_mint_scorer_fails_loud_without_substitute_score(monkeypatch: Any) -> None:
    def fake_call_llm_structured(**_: Any) -> tuple[Any, _FakeLLMResult]:
        raise RuntimeError("provider unavailable")

    fake_module = types.ModuleType("llm_client")
    setattr(fake_module, "call_llm_structured", fake_call_llm_structured)
    monkeypatch.setitem(sys.modules, "llm_client", fake_module)

    scorer = MintScorer(model="minimax/minimax-m3", timeout_seconds=60, max_budget=0.07)
    with pytest.raises(MintScoringError, match="RuntimeError: provider unavailable") as raised:
        scorer.score_artifact(
            artifact_id="artifact_2",
            artifact_type="tool",
            content="short content",
            code="def run():\n    return 'ok'\n",
        )

    assert isinstance(raised.value.__cause__, RuntimeError)
    assert scorer.last_cost == 0.0
    assert scorer.last_error == "RuntimeError: provider unavailable"


class _RaisingScorer(MintScorer):
    def __init__(self) -> None:
        super().__init__(model="unused", timeout_seconds=1)

    def score_artifact(self, artifact_id: str, artifact_type: str, content: str, code: str) -> tuple[int, str]:
        raise MintScoringError(f"mint scoring failed for {artifact_id}: RuntimeError: boom")


class _Logger:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def log(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append((event_type, payload))


def test_auction_scoring_failure_refunds_all_bids_and_raises() -> None:
    ledger = Ledger(rate_tracker=RateTracker())
    ledger.create_principal("alpha_1", starting_scrip=100)
    ledger.create_principal("alpha_2", starting_scrip=100)
    artifact_a = types.SimpleNamespace(
        id="a1", type="text", content="x", code="", owner="alpha_1", deleted=False, auth_state={}
    )
    artifact_b = types.SimpleNamespace(
        id="b1", type="text", content="y", code="", owner="alpha_2", deleted=False, auth_state={}
    )
    artifacts = {"a1": artifact_a, "b1": artifact_b}
    logger = _Logger()
    auction = MintAuction(
        ledger=ledger,
        artifacts=artifacts,
        logger=logger,
        event_number_getter=lambda: 7,
        minimum_bid=1,
        first_auction_delay_seconds=0.0,
        bidding_window_seconds=0.0,
        period_seconds=1.0,
        mint_ratio=10,
        scorer=_RaisingScorer(),
    )
    auction.submit("alpha_1", "a1", 9)
    auction.submit("alpha_2", "b1", 4)
    assert ledger.get_scrip("alpha_1") == 91

    with pytest.raises(MintScoringError, match="boom"):
        auction.resolve()

    assert ledger.get_scrip("alpha_1") == 100
    assert ledger.get_scrip("alpha_2") == 100
    assert auction.get_submissions() == []
    failures = [payload for name, payload in logger.events if name == "mint_scoring_failed"]
    assert len(failures) == 1
    assert failures[0]["winner_id"] == "alpha_1"
    assert failures[0]["bids_refunded"] == {"alpha_1": 9, "alpha_2": 4}
    assert not [name for name, _ in logger.events if name == "mint_auction"]
