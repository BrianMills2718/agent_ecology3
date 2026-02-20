"""Action execution against world state."""

from __future__ import annotations

import json
import time
from typing import Any

from .actions import (
    ActionIntent,
    ActionResult,
    DeleteArtifactIntent,
    EditArtifactIntent,
    InvokeArtifactIntent,
    MintIntent,
    NoopIntent,
    QueryKernelIntent,
    ReadArtifactIntent,
    SubscribeArtifactIntent,
    SubmitToMintIntent,
    TransferIntent,
    UnsubscribeArtifactIntent,
    UpdateMetadataIntent,
    WriteArtifactIntent,
)
from .contracts import PermissionAction


def _extract_action_name(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    action = payload.get("action_type")
    if not isinstance(action, str):
        action = payload.get("action")
    if not isinstance(action, str):
        return None
    normalized = action.strip().lower()
    return normalized or None


class ActionExecutor:
    def __init__(self, world: Any) -> None:
        self.world = world

    def execute(self, intent: ActionIntent) -> ActionResult:
        if isinstance(intent, NoopIntent):
            result = ActionResult(True, "noop")
        elif isinstance(intent, ReadArtifactIntent):
            result = self._read(intent)
        elif isinstance(intent, WriteArtifactIntent):
            result = self._write(intent)
        elif isinstance(intent, EditArtifactIntent):
            result = self._edit(intent)
        elif isinstance(intent, InvokeArtifactIntent):
            result = self._invoke(intent)
        elif isinstance(intent, DeleteArtifactIntent):
            result = self._delete(intent)
        elif isinstance(intent, QueryKernelIntent):
            result = self._query(intent)
        elif isinstance(intent, SubscribeArtifactIntent):
            result = self._subscribe(intent)
        elif isinstance(intent, UnsubscribeArtifactIntent):
            result = self._unsubscribe(intent)
        elif isinstance(intent, TransferIntent):
            result = self._transfer(intent)
        elif isinstance(intent, MintIntent):
            result = self._mint(intent)
        elif isinstance(intent, SubmitToMintIntent):
            result = self._submit_to_mint(intent)
        elif isinstance(intent, UpdateMetadataIntent):
            result = self._update_metadata(intent)
        else:
            result = ActionResult(False, "unknown action")

        self._log_action(intent, result)
        return result

    def _read(self, intent: ReadArtifactIntent) -> ActionResult:
        artifact = self.world.artifacts.get(intent.artifact_id)
        if artifact is None or artifact.deleted:
            return ActionResult(
                False,
                f"artifact '{intent.artifact_id}' not found",
                error_code="not_found",
                error_category="resource",
            )

        perm = self.world.contract_engine.check(intent.principal_id, PermissionAction.READ, artifact)
        if not perm.allowed:
            return ActionResult(
                False,
                f"read not allowed: {perm.reason}",
                error_code="not_authorized",
                error_category="permission",
            )

        read_price = artifact.read_price
        recipient = perm.scrip_recipient or artifact.owner
        if read_price > 0:
            if not self.world.ledger.can_afford_scrip(intent.principal_id, read_price):
                return ActionResult(
                    False,
                    f"cannot afford read price {read_price}",
                    error_code="insufficient_funds",
                    error_category="resource",
                    retriable=True,
                )
            if recipient != intent.principal_id:
                self.world.ledger.transfer_scrip(intent.principal_id, recipient, read_price)

        self.world.logger.log(
            "artifact_read",
            {
                "event_number": self.world.event_number,
                "principal_id": intent.principal_id,
                "artifact_id": artifact.id,
                "read_price_paid": read_price,
                "recipient": recipient,
                "content_size": len(artifact.content),
            },
        )
        return ActionResult(
            True,
            f"read '{artifact.id}'",
            data={"artifact": artifact.to_dict(include_code=False), "read_price_paid": read_price},
        )

    def _write(self, intent: WriteArtifactIntent) -> ActionResult:
        existing = self.world.artifacts.get(intent.artifact_id)
        if existing is not None:
            if existing.deleted:
                return ActionResult(False, f"artifact '{intent.artifact_id}' is deleted")
            if existing.kernel_protected:
                return ActionResult(False, "artifact is kernel_protected", error_code="not_authorized")
            perm = self.world.contract_engine.check(intent.principal_id, PermissionAction.WRITE, existing)
            if not perm.allowed:
                return ActionResult(False, f"write not allowed: {perm.reason}", error_code="not_authorized")

        access_contract_id = intent.access_contract_id
        if existing is None and not access_contract_id:
            access_contract_id = self.world.config.contracts.default_for_new_artifact

        if intent.executable:
            valid, error = self.world.executor.validate_code(intent.code)
            if not valid:
                return ActionResult(
                    False,
                    f"code validation failed: {error}",
                    error_code="invalid_code",
                    error_category="validation",
                    retriable=True,
                )

        new_size = len(intent.content.encode("utf-8")) + len(intent.code.encode("utf-8"))
        old_size = 0
        if existing is not None:
            old_size = len(existing.content.encode("utf-8")) + len(existing.code.encode("utf-8"))
        size_delta = new_size - old_size

        if size_delta > 0:
            available = self.world.get_available_disk(intent.principal_id)
            if available < size_delta:
                return ActionResult(
                    False,
                    f"disk quota exceeded: need {size_delta}, available {available}",
                    error_code="quota_exceeded",
                    error_category="resource",
                    retriable=True,
                )

        artifact = self.world.artifacts.write(
            intent.artifact_id,
            intent.artifact_type,
            intent.content,
            intent.principal_id,
            executable=intent.executable,
            code=intent.code,
            read_price=intent.read_price,
            invoke_price=intent.invoke_price,
            access_contract_id=access_contract_id,
            metadata=intent.metadata,
            interface=intent.interface,
            has_standing=intent.has_standing,
            has_loop=intent.has_loop,
            capabilities=intent.capabilities,
            owner=existing.owner if existing else intent.principal_id,
        )

        if existing is None and artifact.has_standing and not self.world.ledger.principal_exists(artifact.id):
            self.world.ledger.create_principal(artifact.id, starting_scrip=0)
            self.world.set_disk_quota(artifact.id, self.world.config.principals.starting_disk_quota_bytes)
            self.world.logger.log(
                "principal_created",
                {
                    "event_number": self.world.event_number,
                    "principal_id": artifact.id,
                    "created_by": intent.principal_id,
                    "has_loop": artifact.has_loop,
                },
            )

        self.world.logger.log(
            "artifact_written",
            {
                "event_number": self.world.event_number,
                "principal_id": intent.principal_id,
                "artifact_id": artifact.id,
                "artifact_type": artifact.type,
                "executable": artifact.executable,
                "size_bytes": new_size,
                "was_update": existing is not None,
                "has_standing": artifact.has_standing,
                "has_loop": artifact.has_loop,
            },
        )
        return ActionResult(
            True,
            f"{'updated' if existing else 'created'} artifact '{artifact.id}'",
            data={
                "artifact_id": artifact.id,
                "size_bytes": new_size,
                "was_update": existing is not None,
                "principal_created": existing is None and artifact.has_standing,
            },
        )

    def _edit(self, intent: EditArtifactIntent) -> ActionResult:
        artifact = self.world.artifacts.get(intent.artifact_id)
        if artifact is None or artifact.deleted:
            return ActionResult(False, "artifact not found", error_code="not_found")
        if artifact.kernel_protected:
            return ActionResult(False, "artifact is kernel_protected", error_code="not_authorized")

        perm = self.world.contract_engine.check(intent.principal_id, PermissionAction.EDIT, artifact)
        if not perm.allowed:
            return ActionResult(False, f"edit not allowed: {perm.reason}", error_code="not_authorized")

        old_bytes = len(intent.old_string.encode("utf-8"))
        new_bytes = len(intent.new_string.encode("utf-8"))
        size_delta = new_bytes - old_bytes
        if size_delta > 0 and self.world.get_available_disk(intent.principal_id) < size_delta:
            return ActionResult(False, "disk quota exceeded", error_code="quota_exceeded", retriable=True)

        result = self.world.artifacts.edit_artifact(intent.artifact_id, intent.old_string, intent.new_string)
        if not result.success:
            return ActionResult(False, result.message, error_code=(result.data or {}).get("error"))

        self.world.logger.log(
            "artifact_edited",
            {
                "event_number": self.world.event_number,
                "principal_id": intent.principal_id,
                "artifact_id": intent.artifact_id,
                "size_delta": size_delta,
            },
        )
        return ActionResult(True, f"edited '{intent.artifact_id}'", data={"size_delta": size_delta})

    def _invoke(self, intent: InvokeArtifactIntent) -> ActionResult:
        start = time.perf_counter()

        if intent.artifact_id in self.world.kernel_services:
            service = self.world.kernel_services[intent.artifact_id]
            method = service.get("methods", {}).get(intent.method)
            if method is None:
                return ActionResult(False, f"unknown method '{intent.method}' on {intent.artifact_id}", error_code="not_found")
            try:
                payload = method(intent.args, intent.principal_id)
            except Exception as exc:
                return ActionResult(False, f"service error: {exc}", error_code="runtime_error")
            duration_ms = (time.perf_counter() - start) * 1000
            if payload.get("success", False):
                self.world.logger.log(
                    "invoke_success",
                    {
                        "event_number": self.world.event_number,
                        "invoker_id": intent.principal_id,
                        "artifact_id": intent.artifact_id,
                        "method": intent.method,
                        "duration_ms": duration_ms,
                    },
                )
                return ActionResult(True, f"invoked {intent.artifact_id}.{intent.method}", data=payload)

            self.world.logger.log(
                "invoke_failure",
                {
                    "event_number": self.world.event_number,
                    "invoker_id": intent.principal_id,
                    "artifact_id": intent.artifact_id,
                    "method": intent.method,
                    "duration_ms": duration_ms,
                    "error": payload.get("error", "service failed"),
                },
            )
            return ActionResult(False, payload.get("error", "service failed"), error_code=payload.get("error_code"))

        artifact = self.world.artifacts.get(intent.artifact_id)
        if artifact is None or artifact.deleted:
            return ActionResult(False, f"artifact '{intent.artifact_id}' not found", error_code="not_found")
        if not artifact.executable:
            return ActionResult(False, f"artifact '{artifact.id}' is not executable", error_code="invalid_type")

        if intent.method == "describe":
            return ActionResult(
                True,
                f"interface for '{artifact.id}'",
                data={
                    "artifact_id": artifact.id,
                    "type": artifact.type,
                    "owner": artifact.owner,
                    "interface": artifact.interface,
                    "description": artifact.content,
                },
            )

        perm = self.world.contract_engine.check(
            intent.principal_id,
            PermissionAction.INVOKE,
            artifact,
            method=intent.method,
            args=intent.args,
        )
        if not perm.allowed:
            return ActionResult(False, f"invoke not allowed: {perm.reason}", error_code="not_authorized")

        charge_to = str(artifact.metadata.get("charge_to", "caller"))
        try:
            payer = self.world.delegation_manager.resolve_payer(charge_to, intent.principal_id, artifact)
        except ValueError as exc:
            return ActionResult(False, str(exc), error_code="invalid_charge_directive")

        if payer != intent.principal_id:
            authorized, reason = self.world.delegation_manager.authorize_charge(payer, intent.principal_id, float(artifact.invoke_price))
            if not authorized:
                return ActionResult(False, f"delegation denied: {reason}", error_code="not_authorized")

        if artifact.invoke_price > 0 and not self.world.ledger.can_afford_scrip(payer, artifact.invoke_price):
            return ActionResult(False, "insufficient scrip for invoke price", error_code="insufficient_funds", retriable=True)

        entry_point = "handle_request" if "def handle_request(" in artifact.code else "run"
        current_depth = int(getattr(intent, "_invoke_depth", 0))
        max_depth = int(getattr(intent, "_max_invoke_depth", self.world.max_invoke_depth))
        exec_result = self.world.executor.execute_with_invoke(
            code=artifact.code,
            args=intent.args,
            caller_id=intent.principal_id,
            artifact_id=artifact.id,
            world=self.world,
            current_depth=current_depth,
            max_depth=max_depth,
            entry_point=entry_point,
            method_name=intent.method,
        )

        resources = exec_result.get("resources_consumed", {})
        cpu_used = float(resources.get("cpu_seconds", 0.0))
        if cpu_used > 0:
            self.world.ledger.consume_resource(payer, "cpu_seconds", cpu_used)

        duration_ms = float(exec_result.get("execution_time_ms", (time.perf_counter() - start) * 1000))
        if not exec_result.get("success", False):
            self.world.logger.log(
                "invoke_failure",
                {
                    "event_number": self.world.event_number,
                    "invoker_id": intent.principal_id,
                    "artifact_id": artifact.id,
                    "method": intent.method,
                    "duration_ms": duration_ms,
                    "error": exec_result.get("error"),
                },
            )
            return ActionResult(
                False,
                f"execution failed: {exec_result.get('error')}",
                data={"error": exec_result.get("error")},
                resources_consumed={"cpu_seconds": cpu_used} if cpu_used > 0 else None,
                charged_to=payer,
                error_code="runtime_error",
                error_category="execution",
                retriable=False,
            )

        recipient = perm.scrip_recipient or artifact.owner
        if artifact.invoke_price > 0 and recipient != payer:
            self.world.ledger.transfer_scrip(payer, recipient, artifact.invoke_price)
        if payer != intent.principal_id and artifact.invoke_price > 0:
            self.world.delegation_manager.record_charge(payer, intent.principal_id, float(artifact.invoke_price))

        if artifact.has_loop and intent.method == "run":
            payload = exec_result.get("result")
            if isinstance(payload, dict):
                decision = payload.get("decision")
                fallback = payload.get("fallback")
                result_payload = payload.get("result")
                result_success: bool | None = None
                result_error_code: str | None = None
                if isinstance(result_payload, dict):
                    raw_success = result_payload.get("success")
                    if isinstance(raw_success, bool):
                        result_success = raw_success
                    raw_error_code = result_payload.get("error_code")
                    if isinstance(raw_error_code, str) and raw_error_code:
                        result_error_code = raw_error_code
                self.world.logger.log(
                    "loop_decision",
                    {
                        "event_number": self.world.event_number,
                        "principal_id": intent.principal_id,
                        "artifact_id": artifact.id,
                        "decision": decision if isinstance(decision, dict) else None,
                        "decision_action": _extract_action_name(decision),
                        "fallback_used": isinstance(fallback, dict),
                        "fallback": fallback if isinstance(fallback, dict) else None,
                        "fallback_action": _extract_action_name(fallback),
                        "result_success": result_success,
                        "result_error_code": result_error_code,
                    },
                )

        self.world.logger.log(
            "invoke_success",
            {
                "event_number": self.world.event_number,
                "invoker_id": intent.principal_id,
                "artifact_id": artifact.id,
                "method": intent.method,
                "duration_ms": duration_ms,
            },
        )

        return ActionResult(
            True,
            f"invoked '{artifact.id}'",
            data={
                "result": exec_result.get("result"),
                "price_paid": artifact.invoke_price,
                "recipient": recipient,
            },
            resources_consumed={"cpu_seconds": cpu_used} if cpu_used > 0 else None,
            charged_to=payer,
        )

    def _delete(self, intent: DeleteArtifactIntent) -> ActionResult:
        artifact = self.world.artifacts.get(intent.artifact_id)
        if artifact is None:
            return ActionResult(False, f"artifact '{intent.artifact_id}' not found", error_code="not_found")
        if artifact.kernel_protected or intent.artifact_id in self.world.kernel_services:
            return ActionResult(False, "cannot delete kernel artifact", error_code="not_authorized")
        if artifact.deleted:
            return ActionResult(False, "artifact already deleted", error_code="not_found")

        perm = self.world.contract_engine.check(intent.principal_id, PermissionAction.DELETE, artifact)
        if not perm.allowed:
            return ActionResult(False, f"delete not allowed: {perm.reason}", error_code="not_authorized")

        freed = len(artifact.content.encode("utf-8")) + len(artifact.code.encode("utf-8"))
        self.world.artifacts.soft_delete(intent.artifact_id, intent.principal_id)
        self.world.logger.log(
            "artifact_deleted",
            {
                "event_number": self.world.event_number,
                "principal_id": intent.principal_id,
                "artifact_id": intent.artifact_id,
                "freed_bytes": freed,
            },
        )
        return ActionResult(True, f"deleted '{intent.artifact_id}'", data={"freed_bytes": freed})

    def _query(self, intent: QueryKernelIntent) -> ActionResult:
        payload = self.world.query_handler.execute(intent.query_type, intent.params)
        if payload.get("success", False):
            self.world.logger.log(
                "kernel_query",
                {
                    "event_number": self.world.event_number,
                    "principal_id": intent.principal_id,
                    "query_type": intent.query_type,
                    "params": intent.params,
                },
            )
            return ActionResult(True, f"query '{intent.query_type}' succeeded", data=payload)
        return ActionResult(False, payload.get("error", "query failed"), data=payload, error_code=payload.get("error_code"))

    def _subscribe(self, intent: SubscribeArtifactIntent) -> ActionResult:
        return self._update_subscription(intent.principal_id, intent.artifact_id, subscribe=True)

    def _unsubscribe(self, intent: UnsubscribeArtifactIntent) -> ActionResult:
        return self._update_subscription(intent.principal_id, intent.artifact_id, subscribe=False)

    def _update_subscription(self, principal_id: str, artifact_id: str, *, subscribe: bool) -> ActionResult:
        agent_artifact = self.world.artifacts.get(principal_id)
        if agent_artifact is None:
            return ActionResult(False, f"agent artifact '{principal_id}' not found", error_code="not_found")

        target = self.world.artifacts.get(artifact_id)
        if subscribe and target is None:
            return ActionResult(False, f"artifact '{artifact_id}' not found", error_code="not_found")

        try:
            config = json.loads(agent_artifact.content) if agent_artifact.content.strip() else {}
        except json.JSONDecodeError:
            config = {}
        if not isinstance(config, dict):
            config = {}

        subscribed = config.get("subscribed_artifacts", [])
        if not isinstance(subscribed, list):
            subscribed = []

        if subscribe:
            if artifact_id not in subscribed:
                subscribed.append(artifact_id)
                message = f"subscribed to '{artifact_id}'"
            else:
                message = f"already subscribed to '{artifact_id}'"
        else:
            if artifact_id in subscribed:
                subscribed.remove(artifact_id)
                message = f"unsubscribed from '{artifact_id}'"
            else:
                message = f"not subscribed to '{artifact_id}'"

        config["subscribed_artifacts"] = subscribed
        agent_artifact.content = json.dumps(config, indent=2)
        agent_artifact.updated_at = self.world.now_iso()
        return ActionResult(True, message, data={"subscribed_artifacts": subscribed})

    def _transfer(self, intent: TransferIntent) -> ActionResult:
        if intent.amount <= 0:
            return ActionResult(False, "amount must be positive", error_code="invalid_argument")
        if not self.world.ledger.principal_exists(intent.principal_id):
            return ActionResult(False, "sender is not a principal", error_code="not_found")
        if not self.world.ledger.principal_exists(intent.recipient_id):
            return ActionResult(False, "recipient is not a principal", error_code="not_found")
        if not self.world.ledger.transfer_scrip(intent.principal_id, intent.recipient_id, intent.amount):
            return ActionResult(False, "insufficient funds", error_code="insufficient_funds", retriable=True)

        self.world.logger.log(
            "transfer",
            {
                "event_number": self.world.event_number,
                "sender": intent.principal_id,
                "recipient": intent.recipient_id,
                "amount": intent.amount,
                "memo": intent.memo,
            },
        )
        return ActionResult(True, f"transferred {intent.amount} scrip to {intent.recipient_id}")

    def _mint(self, intent: MintIntent) -> ActionResult:
        minter = self.world.artifacts.get(intent.principal_id)
        if minter is None:
            return ActionResult(False, "minter artifact not found", error_code="not_found")
        if "can_mint" not in minter.capabilities:
            return ActionResult(False, "caller lacks can_mint capability", error_code="not_authorized")
        if not self.world.ledger.principal_exists(intent.recipient_id):
            return ActionResult(False, "recipient is not a principal", error_code="not_found")
        if intent.amount <= 0:
            return ActionResult(False, "mint amount must be positive", error_code="invalid_argument")

        self.world.ledger.credit_scrip(intent.recipient_id, intent.amount)
        self.world.logger.log(
            "mint",
            {
                "event_number": self.world.event_number,
                "minter": intent.principal_id,
                "recipient": intent.recipient_id,
                "amount": intent.amount,
                "reason": intent.reason,
            },
        )
        return ActionResult(True, f"minted {intent.amount} to {intent.recipient_id}")

    def _submit_to_mint(self, intent: SubmitToMintIntent) -> ActionResult:
        if self.world.mint_auction is None:
            return ActionResult(False, "mint auction disabled", error_code="not_enabled")
        try:
            submission_id = self.world.mint_auction.submit(intent.principal_id, intent.artifact_id, intent.bid)
        except ValueError as exc:
            return ActionResult(False, str(exc), error_code="invalid_submission", retriable=True)
        return ActionResult(True, f"submitted to mint as {submission_id}", data={"submission_id": submission_id})

    def _update_metadata(self, intent: UpdateMetadataIntent) -> ActionResult:
        artifact = self.world.artifacts.get(intent.artifact_id)
        if artifact is None or artifact.deleted:
            return ActionResult(False, "artifact not found", error_code="not_found")

        perm = self.world.contract_engine.check(intent.principal_id, PermissionAction.WRITE, artifact)
        if not perm.allowed:
            return ActionResult(False, f"metadata update not allowed: {perm.reason}", error_code="not_authorized")

        if intent.value is None:
            artifact.metadata.pop(intent.key, None)
        else:
            artifact.metadata[intent.key] = intent.value
        artifact.updated_at = self.world.now_iso()
        self.world.logger.log(
            "metadata_updated",
            {
                "event_number": self.world.event_number,
                "principal_id": intent.principal_id,
                "artifact_id": intent.artifact_id,
                "key": intent.key,
                "value": intent.value,
            },
        )
        return ActionResult(True, f"metadata '{intent.key}' updated")

    def _log_action(self, intent: ActionIntent, result: ActionResult) -> None:
        self.world.logger.log(
            "action",
            {
                "event_number": self.world.event_number,
                "intent": intent.to_dict(),
                "result": result.to_dict(),
                "scrip_after": self.world.ledger.get_scrip(intent.principal_id),
            },
        )
