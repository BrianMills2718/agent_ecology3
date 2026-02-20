"""Rolling-window rate tracker."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class UsageRecord:
    timestamp: float
    amount: float


@dataclass
class RateTracker:
    window_seconds: float = 60.0
    _limits: dict[str, float] = field(default_factory=dict)
    _usage: dict[str, dict[str, deque[UsageRecord]]] = field(default_factory=dict)

    def configure_limit(self, resource: str, max_per_window: float) -> None:
        if max_per_window < 0:
            raise ValueError("max_per_window must be >= 0")
        self._limits[resource] = max_per_window
        self._usage.setdefault(resource, {})

    def get_limit(self, resource: str) -> float:
        return self._limits.get(resource, float("inf"))

    def _prune(self, agent_id: str, resource: str) -> None:
        bucket = self._usage.setdefault(resource, {}).setdefault(agent_id, deque())
        cutoff = time.time() - self.window_seconds
        while bucket and bucket[0].timestamp < cutoff:
            bucket.popleft()

    def get_usage(self, agent_id: str, resource: str) -> float:
        self._prune(agent_id, resource)
        bucket = self._usage.setdefault(resource, {}).setdefault(agent_id, deque())
        return max(0.0, sum(item.amount for item in bucket))

    def get_remaining(self, agent_id: str, resource: str) -> float:
        limit = self.get_limit(resource)
        usage = self.get_usage(agent_id, resource)
        return max(0.0, limit - usage)

    def has_capacity(self, agent_id: str, resource: str, amount: float = 1.0) -> bool:
        if amount < 0:
            return False
        return self.get_remaining(agent_id, resource) >= amount

    def consume(self, agent_id: str, resource: str, amount: float = 1.0) -> bool:
        if amount < 0:
            return False
        if amount == 0:
            return True
        if not self.has_capacity(agent_id, resource, amount):
            return False
        bucket = self._usage.setdefault(resource, {}).setdefault(agent_id, deque())
        bucket.append(UsageRecord(time.time(), amount))
        return True

    def refund(self, agent_id: str, resource: str, amount: float = 1.0) -> bool:
        """Credit back prior rolling-window usage for reconciliation."""
        if amount <= 0:
            return False
        bucket = self._usage.setdefault(resource, {}).setdefault(agent_id, deque())
        bucket.append(UsageRecord(time.time(), -amount))
        return True

    def time_until_capacity(self, agent_id: str, resource: str, amount: float = 1.0) -> float:
        if amount <= 0:
            return 0.0
        if self.has_capacity(agent_id, resource, amount):
            return 0.0

        self._prune(agent_id, resource)
        bucket = self._usage.setdefault(resource, {}).setdefault(agent_id, deque())
        if not bucket:
            return 0.0

        limit = self.get_limit(resource)
        current = sum(x.amount for x in bucket)
        need_to_expire = current - (limit - amount)
        if need_to_expire <= 0:
            return 0.0

        now = time.time()
        acc = 0.0
        for record in bucket:
            acc += record.amount
            if acc >= need_to_expire:
                return max(0.0, (record.timestamp + self.window_seconds) - now)
        return max(0.0, (bucket[-1].timestamp + self.window_seconds) - now)

    async def wait_for_capacity(
        self,
        agent_id: str,
        resource: str,
        amount: float = 1.0,
        timeout: float | None = None,
        poll_interval: float = 0.1,
    ) -> bool:
        if amount <= 0:
            return True
        deadline = None if timeout is None else time.time() + timeout
        while True:
            if self.consume(agent_id, resource, amount):
                return True
            if deadline is not None and time.time() >= deadline:
                return False
            sleep_for = max(poll_interval, self.time_until_capacity(agent_id, resource, amount))
            await asyncio.sleep(min(sleep_for, poll_interval))
