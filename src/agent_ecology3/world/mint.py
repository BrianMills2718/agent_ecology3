"""Mint auction subsystem."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any


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


class MintScorer:
    """LLM-backed scorer with deterministic fallback."""

    def __init__(self, model: str, timeout_seconds: int) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.last_cost: float = 0.0

    def score_artifact(self, artifact_id: str, artifact_type: str, content: str, code: str) -> tuple[int, str]:
        prompt = (
            "Score this artifact from 0-100 for utility and correctness. "
            "Return JSON: {\"score\": int, \"reason\": str}.\n\n"
            f"Artifact: {artifact_id}\nType: {artifact_type}\n"
            f"Content:\n{content[:4000]}\n\nCode:\n{code[:6000]}"
        )
        messages = [{"role": "user", "content": prompt}]
        try:
            import litellm

            response = litellm.completion(
                model=self.model,
                messages=messages,
                timeout=self.timeout_seconds,
                num_retries=1,
            )
            self.last_cost = float(litellm.completion_cost(completion_response=response))
            payload = response.choices[0].message.content or ""
            start = payload.find("{")
            end = payload.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(payload[start:end])
                score = int(parsed.get("score", 0))
                reason = str(parsed.get("reason", "model score"))
                return max(0, min(100, score)), reason
        except Exception:
            pass

        length_score = min(70, max(10, (len(content) + len(code)) // 120))
        bonus = 20 if "def run(" in code else 0
        score = max(0, min(100, length_score + bonus))
        reason = "fallback score based on artifact complexity"
        self.last_cost = 0.0
        return score, reason


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

        for sub in submissions[1:]:
            self.ledger.credit_scrip(sub.principal_id, sub.bid)

        refund = winner.bid - second_price
        if refund > 0:
            self.ledger.credit_scrip(winner.principal_id, refund)

        artifact = self.artifacts.get(winner.artifact_id)
        if artifact is None:
            score = None
            score_reason = None
            minted = 0
            error = "winner artifact disappeared"
        else:
            score, score_reason = self.scorer.score_artifact(
                artifact.id,
                artifact.type,
                artifact.content,
                artifact.code,
            )
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
