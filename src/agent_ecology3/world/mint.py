"""Mint auction subsystem."""

from __future__ import annotations

from importlib import import_module
import time
import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ArtifactScore(BaseModel):
    """Schema-constrained model response for mint artifact scoring."""

    model_config = ConfigDict(extra="forbid")

    score: int = Field(
        ge=0,
        le=100,
        description="Integer utility and correctness score from 0 to 100.",
    )
    reason: str = Field(description="Short human-readable reason for the score.")


@dataclass
class MintSubmission:
    submission_id: str
    principal_id: str
    artifact_id: str
    bid: int
    submitted_at_event: int


@dataclass
class MintResult:
    winner_id: str | None
    artifact_id: str | None
    winning_bid: int
    price_paid: int
    score: int | None
    score_reason: str | None
    scrip_minted: int
    ubi_distributed: dict[str, int]
    error: str | None
    resolved_at_event: int


class MintScoringError(RuntimeError):
    """The mint scorer could not produce an authentic score.

    Raised instead of substituting a local score: a scoring failure must stop
    the auction visibly rather than mint scrip from a fabricated value.
    """


class MintScorer:
    """LLM-backed scorer. Fails loud; never substitutes a local score."""

    def __init__(self, model: str, timeout_seconds: int, max_budget: float = 0.25) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_budget = max_budget
        self.last_cost: float = 0.0
        self.last_error: str | None = None

    def score_artifact(self, artifact_id: str, artifact_type: str, content: str, code: str) -> tuple[int, str]:
        prompt = (
            "Score this artifact from 0-100 for utility and correctness. "
            "Return a structured score and reason.\n\n"
            f"Artifact: {artifact_id}\nType: {artifact_type}\n"
            f"Content:\n{content[:4000]}\n\nCode:\n{code[:6000]}"
        )
        messages = [{"role": "user", "content": prompt}]
        try:
            call_llm_structured = import_module("llm_client").call_llm_structured

            parsed, result = call_llm_structured(
                model=self.model,
                messages=messages,
                response_model=ArtifactScore,
                num_retries=1,
                task="agent_ecology3_mint_scoring",
                trace_id=f"agent_ecology3.mint_score.{artifact_id}.{uuid.uuid4().hex[:8]}",
                max_budget=self.max_budget,
            )
            self.last_cost = float(result.cost)
            self.last_error = None
            return parsed.score, parsed.reason
        except Exception as exc:
            self.last_cost = 0.0
            self.last_error = f"{type(exc).__name__}: {exc}"
            raise MintScoringError(
                f"mint scoring failed for {artifact_id}: {self.last_error}"
            ) from exc


class MintAuction:
    def __init__(
        self,
        *,
        ledger: Any,
        artifacts: Any,
        logger: Any,
        event_number_getter: Any,
        minimum_bid: int,
        first_auction_delay_seconds: float,
        bidding_window_seconds: float,
        period_seconds: float,
        mint_ratio: int,
        scorer: MintScorer,
    ) -> None:
        self.ledger = ledger
        self.artifacts = artifacts
        self.logger = logger
        self._event_number_getter = event_number_getter

        self.minimum_bid = minimum_bid
        self.first_auction_delay_seconds = first_auction_delay_seconds
        self.bidding_window_seconds = bidding_window_seconds
        self.period_seconds = period_seconds
        self.mint_ratio = mint_ratio
        self.scorer = scorer

        self._submissions: dict[str, MintSubmission] = {}
        self._history: list[MintResult] = []
        self._start_time = time.time()
        self._auction_started_at: float | None = None

    @property
    def event_number(self) -> int:
        return int(self._event_number_getter())

    def get_submissions(self) -> list[dict[str, Any]]:
        return [submission.__dict__ for submission in self._submissions.values()]

    def get_history(self, limit: int = 100) -> list[dict[str, Any]]:
        return [item.__dict__ for item in self._history[-limit:]]

    def submit(self, principal_id: str, artifact_id: str, bid: int) -> str:
        artifact = self.artifacts.get(artifact_id)
        if artifact is None or artifact.deleted:
            raise ValueError(f"artifact '{artifact_id}' not found")
        if bid < self.minimum_bid:
            raise ValueError(f"bid must be >= {self.minimum_bid}")
        if not self.ledger.can_afford_scrip(principal_id, bid):
            raise ValueError("insufficient scrip for bid")

        writer = artifact.auth_state.get("writer")
        principal = artifact.auth_state.get("principal")
        if principal_id not in {artifact.owner, writer, principal}:
            raise ValueError("submitter is not authorized for artifact")

        self.ledger.deduct_scrip(principal_id, bid)
        submission_id = f"mint_sub_{uuid.uuid4().hex[:10]}"
        self._submissions[submission_id] = MintSubmission(
            submission_id=submission_id,
            principal_id=principal_id,
            artifact_id=artifact_id,
            bid=bid,
            submitted_at_event=self.event_number,
        )
        self.logger.log(
            "mint_submission",
            {
                "event_number": self.event_number,
                "principal_id": principal_id,
                "artifact_id": artifact_id,
                "bid": bid,
                "submission_id": submission_id,
            },
        )
        return submission_id

    def cancel(self, principal_id: str, submission_id: str) -> bool:
        submission = self._submissions.get(submission_id)
        if submission is None:
            return False
        if submission.principal_id != principal_id:
            return False
        self.ledger.credit_scrip(principal_id, submission.bid)
        del self._submissions[submission_id]
        self.logger.log(
            "mint_submission_cancelled",
            {
                "event_number": self.event_number,
                "submission_id": submission_id,
                "principal_id": principal_id,
            },
        )
        return True

    def status(self) -> dict[str, Any]:
        now = time.time()
        if now - self._start_time < self.first_auction_delay_seconds:
            phase = "waiting_first_auction"
        elif self._auction_started_at is None:
            phase = "waiting_bidding_window"
        elif now - self._auction_started_at < self.bidding_window_seconds:
            phase = "bidding"
        else:
            phase = "resolving"
        return {
            "phase": phase,
            "pending_submissions": len(self._submissions),
            "history_count": len(self._history),
        }

    def update(self) -> dict[str, Any] | None:
        now = time.time()
        if now - self._start_time < self.first_auction_delay_seconds:
            return None

        if self._auction_started_at is None:
            self._auction_started_at = now
            return None

        elapsed = now - self._auction_started_at
        if elapsed >= self.bidding_window_seconds:
            result = self.resolve()
            if elapsed >= self.period_seconds:
                self._auction_started_at = now
            else:
                self._auction_started_at += self.period_seconds
            return result
        return None

    def resolve(self) -> dict[str, Any]:
        if not self._submissions:
            result = MintResult(
                winner_id=None,
                artifact_id=None,
                winning_bid=0,
                price_paid=0,
                score=None,
                score_reason=None,
                scrip_minted=0,
                ubi_distributed={},
                error="no submissions",
                resolved_at_event=self.event_number,
            )
            self._history.append(result)
            return result.__dict__

        submissions = list(self._submissions.values())
        submissions.sort(key=lambda item: item.bid, reverse=True)

        winner = submissions[0]
        second_price = submissions[1].bid if len(submissions) > 1 else self.minimum_bid

        # Score before any ledger change so a scoring failure leaves balances
        # exactly as they were (all bids refunded) and stops visibly.
        artifact = self.artifacts.get(winner.artifact_id)
        score: int | None = None
        score_reason: str | None = None
        if artifact is not None:
            try:
                score, score_reason = self.scorer.score_artifact(
                    artifact.id,
                    artifact.type,
                    artifact.content,
                    artifact.code,
                )
            except MintScoringError as exc:
                for sub in submissions:
                    self.ledger.credit_scrip(sub.principal_id, sub.bid)
                self._submissions.clear()
                self.logger.log(
                    "mint_scoring_failed",
                    {
                        "event_number": self.event_number,
                        "artifact_id": winner.artifact_id,
                        "winner_id": winner.principal_id,
                        "error": str(exc),
                        "bids_refunded": {sub.principal_id: sub.bid for sub in submissions},
                    },
                )
                raise

        for sub in submissions[1:]:
            self.ledger.credit_scrip(sub.principal_id, sub.bid)

        refund = winner.bid - second_price
        if refund > 0:
            self.ledger.credit_scrip(winner.principal_id, refund)

        if artifact is None or score is None:
            minted = 0
            error = "winner artifact disappeared"
        else:
            minted = score // max(1, self.mint_ratio)
            error = None
            if minted > 0:
                self.ledger.credit_scrip(winner.principal_id, minted)

        ubi = self.ledger.distribute_ubi(second_price, exclude=winner.principal_id)
        result = MintResult(
            winner_id=winner.principal_id,
            artifact_id=winner.artifact_id,
            winning_bid=winner.bid,
            price_paid=second_price,
            score=score,
            score_reason=score_reason,
            scrip_minted=minted,
            ubi_distributed=ubi,
            error=error,
            resolved_at_event=self.event_number,
        )

        self._history.append(result)
        self._submissions.clear()
        self.logger.log("mint_auction", {"event_number": self.event_number, **result.__dict__})
        return result.__dict__
