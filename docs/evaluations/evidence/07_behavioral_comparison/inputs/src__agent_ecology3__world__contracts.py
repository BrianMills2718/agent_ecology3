"""Contract-based access control."""

from __future__ import annotations

import builtins
import signal
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from types import FrameType
from typing import Any, Generator, Protocol


KERNEL_CONTRACT_FREEWARE = "kernel_contract_freeware"
KERNEL_CONTRACT_TRANSFERABLE_FREEWARE = "kernel_contract_transferable_freeware"
KERNEL_CONTRACT_SELF_OWNED = "kernel_contract_self_owned"
KERNEL_CONTRACT_PRIVATE = "kernel_contract_private"
KERNEL_CONTRACT_PUBLIC = "kernel_contract_public"


class PermissionAction(str, Enum):
    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    INVOKE = "invoke"
    DELETE = "delete"


@dataclass
class PermissionResult:
    allowed: bool
    reason: str
    scrip_cost: int = 0
    scrip_payer: str | None = None
    scrip_recipient: str | None = None
    resource_payer: str | None = None
    state_updates: dict[str, object] | None = None
    conditions: dict[str, object] | None = None


class AccessContract(Protocol):
    contract_id: str
    contract_type: str

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: dict[str, object] | None = None,
    ) -> PermissionResult:
        ...


class ReadOnlyLedger:
    """Read-only facade for contract code."""

    def __init__(self, ledger: Any) -> None:
        self._ledger = ledger

    def get_scrip(self, principal_id: str) -> int:
        return self._ledger.get_scrip(principal_id)

    def can_afford_scrip(self, principal_id: str, amount: int) -> bool:
        return self._ledger.can_afford_scrip(principal_id, amount)

    def get_resource(self, principal_id: str, resource: str) -> float:
        return self._ledger.get_resource(principal_id, resource)

    def principal_exists(self, principal_id: str) -> bool:
        return self._ledger.principal_exists(principal_id)


@dataclass
class FreewareContract:
    contract_id: str = KERNEL_CONTRACT_FREEWARE
    contract_type: str = "freeware"

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: dict[str, object] | None = None,
    ) -> PermissionResult:
        state = context.get("_artifact_state", {}) if context else {}
        writer = state.get("writer") if isinstance(state, dict) else None
        if action in (PermissionAction.READ, PermissionAction.INVOKE):
            return PermissionResult(True, "freeware open access", scrip_recipient=str(writer) if writer else None)
        if writer is not None and caller == writer:
            return PermissionResult(True, "freeware writer access", scrip_recipient=str(writer))
        return PermissionResult(False, "freeware only writer can modify")


@dataclass
class TransferableFreewareContract:
    contract_id: str = KERNEL_CONTRACT_TRANSFERABLE_FREEWARE
    contract_type: str = "transferable_freeware"

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: dict[str, object] | None = None,
    ) -> PermissionResult:
        return FreewareContract().check_permission(caller, action, target, context)


@dataclass
class SelfOwnedContract:
    contract_id: str = KERNEL_CONTRACT_SELF_OWNED
    contract_type: str = "self_owned"

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: dict[str, object] | None = None,
    ) -> PermissionResult:
        state = context.get("_artifact_state", {}) if context else {}
        principal = state.get("principal") if isinstance(state, dict) else None
        if caller == target:
            return PermissionResult(True, "self access", scrip_recipient=str(principal) if principal else None)
        if principal is not None and caller == principal:
            return PermissionResult(True, "principal access", scrip_recipient=str(principal))
        return PermissionResult(False, "self_owned access denied")


@dataclass
class PrivateContract:
    contract_id: str = KERNEL_CONTRACT_PRIVATE
    contract_type: str = "private"

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: dict[str, object] | None = None,
    ) -> PermissionResult:
        state = context.get("_artifact_state", {}) if context else {}
        principal = state.get("principal") if isinstance(state, dict) else None
        if principal is not None and caller == principal:
            return PermissionResult(True, "private principal access", scrip_recipient=str(principal))
        return PermissionResult(False, "private access denied")


@dataclass
class PublicContract:
    contract_id: str = KERNEL_CONTRACT_PUBLIC
    contract_type: str = "public"

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: dict[str, object] | None = None,
    ) -> PermissionResult:
        return PermissionResult(True, "public access")


def _timeout_handler(_signum: int, _frame: FrameType | None) -> None:
    raise TimeoutError("contract execution timed out")


@contextmanager
def _timeout_context(seconds: int) -> Generator[None, None, None]:
    old_handler: Any = None
    try:
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(seconds)
    except (ValueError, AttributeError):
        pass

    try:
        yield
    finally:
        try:
            signal.alarm(0)
            if old_handler is not None:
                signal.signal(signal.SIGALRM, old_handler)
        except (ValueError, AttributeError):
            pass


@dataclass
class ExecutableContract:
    contract_id: str
    code: str
    contract_type: str = "custom"
    timeout_seconds: int = 5

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: dict[str, object] | None = None,
        *,
        ledger: Any | None = None,
    ) -> PermissionResult:
        safe_builtins: dict[str, Any] = dict(vars(builtins))
        globals_dict: dict[str, Any] = {"__builtins__": safe_builtins}
        locals_dict: dict[str, Any] = {}

        with _timeout_context(self.timeout_seconds):
            exec(compile(self.code, "<contract>", "exec"), globals_dict, locals_dict)

        func = locals_dict.get("check_permission") or globals_dict.get("check_permission")
        if not callable(func):
            return PermissionResult(False, "contract missing check_permission()")

        kwargs: dict[str, Any] = {
            "caller": caller,
            "action": action.value,
            "target": target,
            "context": context or {},
        }
        if ledger is not None:
            kwargs["ledger"] = ReadOnlyLedger(ledger)

        with _timeout_context(self.timeout_seconds):
            raw = func(**kwargs)

        if isinstance(raw, PermissionResult):
            return raw
        if not isinstance(raw, dict):
            return PermissionResult(False, "contract returned non-dict")
        return PermissionResult(
            allowed=bool(raw.get("allowed", False)),
            reason=str(raw.get("reason", "contract decision")),
            scrip_cost=int(raw.get("scrip_cost", 0) or 0),
            scrip_payer=raw.get("scrip_payer"),
            scrip_recipient=raw.get("scrip_recipient"),
            resource_payer=raw.get("resource_payer"),
            state_updates=raw.get("state_updates"),
            conditions=raw.get("conditions"),
        )


class ContractEngine:
    """Resolves and evaluates contracts for artifact permissions."""

    def __init__(self, artifact_store: Any, ledger: Any, *, default_when_missing: str) -> None:
        self._artifact_store = artifact_store
        self._ledger = ledger
        self._default_when_missing = default_when_missing
        self._kernel_contracts: dict[str, AccessContract] = {
            KERNEL_CONTRACT_FREEWARE: FreewareContract(),
            KERNEL_CONTRACT_TRANSFERABLE_FREEWARE: TransferableFreewareContract(),
            KERNEL_CONTRACT_SELF_OWNED: SelfOwnedContract(),
            KERNEL_CONTRACT_PRIVATE: PrivateContract(),
            KERNEL_CONTRACT_PUBLIC: PublicContract(),
        }

    def _resolve_contract(self, contract_id: str) -> AccessContract | ExecutableContract:
        if contract_id in self._kernel_contracts:
            return self._kernel_contracts[contract_id]

        contract_artifact = self._artifact_store.get(contract_id)
        if contract_artifact and contract_artifact.executable and "def check_permission(" in contract_artifact.code:
            return ExecutableContract(contract_id=contract_id, code=contract_artifact.code)

        fallback = self._kernel_contracts.get(self._default_when_missing)
        if fallback is not None:
            return fallback
        return self._kernel_contracts[KERNEL_CONTRACT_FREEWARE]

    def check(
        self,
        caller: str,
        action: PermissionAction,
        artifact: Any,
        *,
        method: str | None = None,
        args: list[Any] | None = None,
    ) -> PermissionResult:
        context: dict[str, object] = {
            "target_created_by": artifact.created_by,
            "target_metadata": artifact.metadata,
            "_artifact_state": dict(artifact.auth_state or {}),
        }
        if method is not None:
            context["method"] = method
        if args is not None:
            context["args"] = args

        contract_id = artifact.access_contract_id or self._default_when_missing
        contract = self._resolve_contract(contract_id)
        if isinstance(contract, ExecutableContract):
            result = contract.check_permission(
                caller=caller,
                action=action,
                target=artifact.id,
                context=context,
                ledger=self._ledger,
            )
        else:
            result = contract.check_permission(caller=caller, action=action, target=artifact.id, context=context)

        if result.state_updates:
            artifact.auth_state.update(result.state_updates)
        return result


def action_from_string(action: str) -> PermissionAction:
    try:
        return PermissionAction(action)
    except ValueError:
        return PermissionAction.READ
