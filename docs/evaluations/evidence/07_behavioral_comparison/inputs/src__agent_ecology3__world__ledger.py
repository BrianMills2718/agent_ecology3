"""Ledger tracking scrip and resources."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .rates import RateTracker


@dataclass
class Ledger:
    rate_tracker: RateTracker
    scrip: dict[str, int] = field(default_factory=dict)
    resources: dict[str, dict[str, float]] = field(default_factory=lambda: defaultdict(dict))

    def create_principal(
        self,
        principal_id: str,
        *,
        starting_scrip: int = 0,
        starting_resources: dict[str, float] | None = None,
    ) -> None:
        self.scrip.setdefault(principal_id, starting_scrip)
        self.resources.setdefault(principal_id, {})
        if starting_resources:
            for name, value in starting_resources.items():
                self.resources[principal_id][name] = float(value)

    def principal_exists(self, principal_id: str) -> bool:
        return principal_id in self.scrip or principal_id in self.resources

    def ensure_principal(self, principal_id: str) -> None:
        self.scrip.setdefault(principal_id, 0)
        self.resources.setdefault(principal_id, {})

    # ---- scrip ----

    def get_scrip(self, principal_id: str) -> int:
        return self.scrip.get(principal_id, 0)

    def get_all_scrip(self) -> dict[str, int]:
        return dict(self.scrip)

    def can_afford_scrip(self, principal_id: str, amount: int) -> bool:
        return self.get_scrip(principal_id) >= amount

    def credit_scrip(self, principal_id: str, amount: int) -> None:
        self.ensure_principal(principal_id)
        self.scrip[principal_id] += amount

    def deduct_scrip(self, principal_id: str, amount: int) -> bool:
        if amount < 0:
            return False
        if not self.can_afford_scrip(principal_id, amount):
            return False
        self.scrip[principal_id] -= amount
        return True

    def transfer_scrip(self, from_id: str, to_id: str, amount: int) -> bool:
        if amount <= 0:
            return False
        if not self.deduct_scrip(from_id, amount):
            return False
        self.credit_scrip(to_id, amount)
        return True

    def distribute_ubi(self, amount: int, exclude: str | None = None) -> dict[str, int]:
        recipients = [pid for pid in self.scrip if not pid.startswith("SYSTEM")]
        if exclude is not None:
            recipients = [pid for pid in recipients if pid != exclude]
        if amount <= 0 or not recipients:
            return {}
        per = amount // len(recipients)
        rem = amount % len(recipients)
        payout: dict[str, int] = {}
        for idx, pid in enumerate(recipients):
            share = per + (1 if idx < rem else 0)
            if share > 0:
                self.credit_scrip(pid, share)
                payout[pid] = share
        return payout

    # ---- generic resources ----

    def get_resource(self, principal_id: str, resource: str) -> float:
        return float(self.resources.get(principal_id, {}).get(resource, 0.0))

    def set_resource(self, principal_id: str, resource: str, amount: float) -> None:
        self.ensure_principal(principal_id)
        self.resources[principal_id][resource] = float(amount)

    def credit_resource(self, principal_id: str, resource: str, amount: float) -> None:
        self.ensure_principal(principal_id)
        self.resources[principal_id][resource] = self.get_resource(principal_id, resource) + float(amount)

    def can_spend_resource(self, principal_id: str, resource: str, amount: float) -> bool:
        return self.get_resource(principal_id, resource) >= amount

    def spend_resource(self, principal_id: str, resource: str, amount: float) -> bool:
        if amount < 0:
            return False
        if not self.can_spend_resource(principal_id, resource, amount):
            return False
        self.resources[principal_id][resource] = self.get_resource(principal_id, resource) - amount
        return True

    def transfer_resource(self, from_id: str, to_id: str, resource: str, amount: float) -> bool:
        if amount <= 0:
            return False
        if not self.spend_resource(from_id, resource, amount):
            return False
        self.credit_resource(to_id, resource, amount)
        return True

    def get_all_resources(self, principal_id: str) -> dict[str, float]:
        return dict(self.resources.get(principal_id, {}))

    # ---- llm budget ----

    def get_llm_budget(self, principal_id: str) -> float:
        return self.get_resource(principal_id, "llm_budget")

    def can_afford_llm_call(self, principal_id: str, estimated_cost: float) -> bool:
        return self.get_llm_budget(principal_id) >= estimated_cost

    def deduct_llm_cost(self, principal_id: str, actual_cost: float) -> bool:
        return self.spend_resource(principal_id, "llm_budget", actual_cost)

    # ---- rate-limited resources ----

    def check_resource_capacity(self, principal_id: str, resource: str, amount: float = 1.0) -> bool:
        return self.rate_tracker.has_capacity(principal_id, resource, amount)

    def consume_resource(self, principal_id: str, resource: str, amount: float = 1.0) -> bool:
        return self.rate_tracker.consume(principal_id, resource, amount)

    def refund_resource_usage(self, principal_id: str, resource: str, amount: float = 1.0) -> bool:
        return self.rate_tracker.refund(principal_id, resource, amount)

    def get_resource_remaining(self, principal_id: str, resource: str) -> float:
        return self.rate_tracker.get_remaining(principal_id, resource)

    def get_all_balances(self) -> dict[str, dict[str, Any]]:
        principals = set(self.scrip) | set(self.resources)
        return {
            pid: {
                "scrip": self.get_scrip(pid),
                "resources": self.get_all_resources(pid),
            }
            for pid in principals
        }
