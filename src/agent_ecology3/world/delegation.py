"""Charge delegation for invoke price/resource attribution."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class DelegationEntry:
    charger_id: str
    max_per_call: float | None = None
    max_per_window: float | None = None
    window_seconds: int = 3600
    expires_at: str | None = None


@dataclass
class ChargeRecord:
    timestamp: float
    amount: float


class DelegationManager:
    def __init__(self, max_history: int = 1000) -> None:
        self._entries_by_payer: dict[str, dict[str, DelegationEntry]] = defaultdict(dict)
        self._history: dict[tuple[str, str], deque[ChargeRecord]] = defaultdict(deque)
        self.max_history = max_history

    def grant(
        self,
        payer_id: str,
        charger_id: str,
        *,
        max_per_call: float | None = None,
        max_per_window: float | None = None,
        window_seconds: int = 3600,
        expires_at: str | None = None,
    ) -> bool:
        self._entries_by_payer[payer_id][charger_id] = DelegationEntry(
            charger_id=charger_id,
            max_per_call=max_per_call,
            max_per_window=max_per_window,
            window_seconds=window_seconds,
            expires_at=expires_at,
        )
        return True

    def revoke(self, payer_id: str, charger_id: str) -> bool:
        entries = self._entries_by_payer.get(payer_id)
        if not entries or charger_id not in entries:
            return False
        del entries[charger_id]
        return True

    def authorize_charge(self, payer_id: str, charger_id: str, amount: float) -> tuple[bool, str]:
        payer_entries = self._entries_by_payer.get(payer_id, {})
        entry = payer_entries.get(charger_id)
        if entry is None:
            return False, "no delegation"

        if entry.expires_at is not None:
            try:
                if datetime.utcnow() >= datetime.fromisoformat(entry.expires_at):
                    return False, "delegation expired"
            except ValueError:
                return False, "invalid expires_at"

        if entry.max_per_call is not None and amount > entry.max_per_call:
            return False, "exceeds per-call cap"

        if entry.max_per_window is not None:
            used = self._window_usage(payer_id, charger_id, entry.window_seconds)
            if used + amount > entry.max_per_window:
                return False, "exceeds window cap"

        return True, "ok"

    def record_charge(self, payer_id: str, charger_id: str, amount: float) -> None:
        key = (payer_id, charger_id)
        bucket = self._history[key]
        bucket.append(ChargeRecord(time.time(), amount))
        while len(bucket) > self.max_history:
            bucket.popleft()

    def _window_usage(self, payer_id: str, charger_id: str, window_seconds: int) -> float:
        key = (payer_id, charger_id)
        bucket = self._history.get(key)
        if not bucket:
            return 0.0
        now = time.time()
        cutoff = now - window_seconds
        while bucket and bucket[0].timestamp < cutoff:
            bucket.popleft()
        return sum(item.amount for item in bucket)

    @staticmethod
    def resolve_payer(charge_to: str, caller_id: str, target_artifact: Any) -> str:
        if charge_to == "caller":
            return caller_id
        if charge_to in {"target", "contract"}:
            principal = target_artifact.auth_state.get("principal")
            writer = target_artifact.auth_state.get("writer")
            if isinstance(principal, str) and principal:
                return principal
            if isinstance(writer, str) and writer:
                return writer
            return target_artifact.owner
        if charge_to.startswith("pool:"):
            pool_id = charge_to.split(":", 1)[1].strip()
            if pool_id:
                return pool_id
        raise ValueError(f"unsupported charge_to directive: {charge_to}")

    def as_dict(self, payer_id: str) -> dict[str, Any]:
        entries = self._entries_by_payer.get(payer_id, {})
        return {
            "payer": payer_id,
            "delegations": [entry.__dict__ for entry in entries.values()],
        }
