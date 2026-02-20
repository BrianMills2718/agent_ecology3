"""Action intent definitions and JSON parsing."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    NOOP = "noop"
    READ_ARTIFACT = "read_artifact"
    WRITE_ARTIFACT = "write_artifact"
    EDIT_ARTIFACT = "edit_artifact"
    DELETE_ARTIFACT = "delete_artifact"
    INVOKE_ARTIFACT = "invoke_artifact"
    QUERY_KERNEL = "query_kernel"
    SUBSCRIBE_ARTIFACT = "subscribe_artifact"
    UNSUBSCRIBE_ARTIFACT = "unsubscribe_artifact"
    TRANSFER = "transfer"
    MINT = "mint"
    SUBMIT_TO_MINT = "submit_to_mint"
    UPDATE_METADATA = "update_metadata"


KNOWN_QUERY_TYPES: set[str] = {
    "artifacts",
    "artifact",
    "principals",
    "principal",
    "balances",
    "resources",
    "quotas",
    "mint",
    "events",
    "frozen",
    "libraries",
    "dependencies",
}


@dataclass
class ActionIntent:
    action_type: ActionType
    principal_id: str
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "principal_id": self.principal_id,
            "reasoning": self.reasoning,
        }


@dataclass
class NoopIntent(ActionIntent):
    def __init__(self, principal_id: str, reasoning: str = "") -> None:
        super().__init__(ActionType.NOOP, principal_id, reasoning)


@dataclass
class ReadArtifactIntent(ActionIntent):
    artifact_id: str = ""

    def __init__(self, principal_id: str, artifact_id: str, reasoning: str = "") -> None:
        super().__init__(ActionType.READ_ARTIFACT, principal_id, reasoning)
        self.artifact_id = artifact_id

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["artifact_id"] = self.artifact_id
        return d


@dataclass
class WriteArtifactIntent(ActionIntent):
    artifact_id: str = ""
    artifact_type: str = "generic"
    content: str = ""
    executable: bool = False
    code: str = ""
    read_price: int = 0
    invoke_price: int = 0
    access_contract_id: str | None = None
    metadata: dict[str, Any] | None = None
    interface: dict[str, Any] | None = None
    has_standing: bool = False
    has_loop: bool = False
    capabilities: list[str] = field(default_factory=list)

    def __init__(
        self,
        principal_id: str,
        artifact_id: str,
        artifact_type: str,
        content: str,
        *,
        executable: bool = False,
        code: str = "",
        read_price: int = 0,
        invoke_price: int = 0,
        access_contract_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        interface: dict[str, Any] | None = None,
        has_standing: bool = False,
        has_loop: bool = False,
        capabilities: list[str] | None = None,
        reasoning: str = "",
    ) -> None:
        super().__init__(ActionType.WRITE_ARTIFACT, principal_id, reasoning)
        self.artifact_id = artifact_id
        self.artifact_type = artifact_type
        self.content = content
        self.executable = executable
        self.code = code
        self.read_price = read_price
        self.invoke_price = invoke_price
        self.access_contract_id = access_contract_id
        self.metadata = metadata
        self.interface = interface
        self.has_standing = has_standing or has_loop
        self.has_loop = has_loop
        self.capabilities = capabilities or []

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "artifact_id": self.artifact_id,
                "artifact_type": self.artifact_type,
                "content": self.content,
                "executable": self.executable,
                "code": self.code,
                "read_price": self.read_price,
                "invoke_price": self.invoke_price,
                "access_contract_id": self.access_contract_id,
                "metadata": self.metadata,
                "interface": self.interface,
                "has_standing": self.has_standing,
                "has_loop": self.has_loop,
                "capabilities": self.capabilities,
            }
        )
        return d


@dataclass
class EditArtifactIntent(ActionIntent):
    artifact_id: str = ""
    old_string: str = ""
    new_string: str = ""

    def __init__(
        self,
        principal_id: str,
        artifact_id: str,
        old_string: str,
        new_string: str,
        reasoning: str = "",
    ) -> None:
        super().__init__(ActionType.EDIT_ARTIFACT, principal_id, reasoning)
        self.artifact_id = artifact_id
        self.old_string = old_string
        self.new_string = new_string

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "artifact_id": self.artifact_id,
                "old_string": self.old_string,
                "new_string": self.new_string,
            }
        )
        return d


@dataclass
class InvokeArtifactIntent(ActionIntent):
    artifact_id: str = ""
    method: str = "run"
    args: list[Any] = field(default_factory=list)

    def __init__(
        self,
        principal_id: str,
        artifact_id: str,
        method: str,
        args: list[Any] | None = None,
        reasoning: str = "",
    ) -> None:
        super().__init__(ActionType.INVOKE_ARTIFACT, principal_id, reasoning)
        self.artifact_id = artifact_id
        self.method = method
        self.args = args or []

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({"artifact_id": self.artifact_id, "method": self.method, "args": self.args})
        return d


@dataclass
class DeleteArtifactIntent(ActionIntent):
    artifact_id: str = ""

    def __init__(self, principal_id: str, artifact_id: str, reasoning: str = "") -> None:
        super().__init__(ActionType.DELETE_ARTIFACT, principal_id, reasoning)
        self.artifact_id = artifact_id

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["artifact_id"] = self.artifact_id
        return d


@dataclass
class QueryKernelIntent(ActionIntent):
    query_type: str = ""
    params: dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        principal_id: str,
        query_type: str,
        params: dict[str, Any] | None = None,
        reasoning: str = "",
    ) -> None:
        super().__init__(ActionType.QUERY_KERNEL, principal_id, reasoning)
        self.query_type = query_type
        self.params = params or {}

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({"query_type": self.query_type, "params": self.params})
        return d


@dataclass
class SubscribeArtifactIntent(ActionIntent):
    artifact_id: str = ""

    def __init__(self, principal_id: str, artifact_id: str, reasoning: str = "") -> None:
        super().__init__(ActionType.SUBSCRIBE_ARTIFACT, principal_id, reasoning)
        self.artifact_id = artifact_id

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["artifact_id"] = self.artifact_id
        return d


@dataclass
class UnsubscribeArtifactIntent(ActionIntent):
    artifact_id: str = ""

    def __init__(self, principal_id: str, artifact_id: str, reasoning: str = "") -> None:
        super().__init__(ActionType.UNSUBSCRIBE_ARTIFACT, principal_id, reasoning)
        self.artifact_id = artifact_id

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["artifact_id"] = self.artifact_id
        return d


@dataclass
class TransferIntent(ActionIntent):
    recipient_id: str = ""
    amount: int = 0
    memo: str | None = None

    def __init__(
        self,
        principal_id: str,
        recipient_id: str,
        amount: int,
        memo: str | None = None,
        reasoning: str = "",
    ) -> None:
        super().__init__(ActionType.TRANSFER, principal_id, reasoning)
        self.recipient_id = recipient_id
        self.amount = amount
        self.memo = memo

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "recipient_id": self.recipient_id,
                "amount": self.amount,
                "memo": self.memo,
            }
        )
        return d


@dataclass
class MintIntent(ActionIntent):
    recipient_id: str = ""
    amount: int = 0
    reason: str = ""

    def __init__(
        self,
        principal_id: str,
        recipient_id: str,
        amount: int,
        reason: str,
        reasoning: str = "",
    ) -> None:
        super().__init__(ActionType.MINT, principal_id, reasoning)
        self.recipient_id = recipient_id
        self.amount = amount
        self.reason = reason

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "recipient_id": self.recipient_id,
                "amount": self.amount,
                "reason": self.reason,
            }
        )
        return d


@dataclass
class SubmitToMintIntent(ActionIntent):
    artifact_id: str = ""
    bid: int = 0

    def __init__(self, principal_id: str, artifact_id: str, bid: int, reasoning: str = "") -> None:
        super().__init__(ActionType.SUBMIT_TO_MINT, principal_id, reasoning)
        self.artifact_id = artifact_id
        self.bid = bid

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "artifact_id": self.artifact_id,
                "bid": self.bid,
            }
        )
        return d


@dataclass
class UpdateMetadataIntent(ActionIntent):
    artifact_id: str = ""
    key: str = ""
    value: object = None

    def __init__(
        self,
        principal_id: str,
        artifact_id: str,
        key: str,
        value: object,
        reasoning: str = "",
    ) -> None:
        super().__init__(ActionType.UPDATE_METADATA, principal_id, reasoning)
        self.artifact_id = artifact_id
        self.key = key
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "artifact_id": self.artifact_id,
                "key": self.key,
                "value": self.value,
            }
        )
        return d


@dataclass
class ActionResult:
    success: bool
    message: str
    data: dict[str, Any] | None = None
    resources_consumed: dict[str, float] | None = None
    charged_to: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    retriable: bool = False
    error_details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "success": self.success,
            "message": self.message,
            "data": self.data,
        }
        if self.resources_consumed:
            payload["resources_consumed"] = self.resources_consumed
        if self.charged_to:
            payload["charged_to"] = self.charged_to
        if self.error_code:
            payload["error_code"] = self.error_code
            payload["error_category"] = self.error_category
            payload["retriable"] = self.retriable
        if self.error_details is not None:
            payload["error_details"] = self.error_details
        return payload


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
    return None


def _infer_query_type(
    query_text: str,
    *,
    principal_id: str,
) -> tuple[str, dict[str, Any]]:
    lowered = query_text.strip().lower()
    if lowered in KNOWN_QUERY_TYPES:
        return lowered, {}

    if any(token in lowered for token in ("mint", "auction", "bid")):
        return "mint", {}
    if any(token in lowered for token in ("event", "history", "log", "timeline", "status", "state", "time")):
        return "events", {"limit": 20}
    if any(token in lowered for token in ("resource", "quota", "budget", "cpu", "token")):
        return "resources", {"principal_id": principal_id}
    if any(token in lowered for token in ("balance", "scrip", "currency")):
        return "balances", {"principal_id": principal_id}
    if "frozen" in lowered:
        return "frozen", {}
    if "library" in lowered:
        return "libraries", {"principal_id": principal_id}
    if "depend" in lowered:
        return "artifacts", {"limit": 50}
    if any(token in lowered for token in ("principal", "agent")):
        if "self" in lowered:
            return "principal", {"principal_id": principal_id}
        return "principals", {}
    if "artifact" in lowered:
        return "artifacts", {"limit": 50}
    return "balances", {"principal_id": principal_id}


def _normalize_payload(principal_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)

    parameters = data.get("parameters")
    if isinstance(parameters, dict):
        for key, value in parameters.items():
            data.setdefault(key, value)

    if "query_type" not in data and isinstance(data.get("queryType"), str):
        data["query_type"] = data["queryType"]
    if "recipient_id" not in data and isinstance(data.get("recipient"), str):
        data["recipient_id"] = data["recipient"]
    if "method" not in data and isinstance(data.get("fn"), str):
        data["method"] = data["fn"]

    action_type_raw = str(data.get("action_type", "")).strip().lower()
    action_alias = data.get("action")
    if isinstance(action_alias, str):
        alias = action_alias.strip().lower()
        if alias and (not action_type_raw or action_type_raw == ActionType.NOOP.value) and alias != ActionType.NOOP.value:
            action_type_raw = alias
            data["action_type"] = alias

    if action_type_raw == ActionType.QUERY_KERNEL.value:
        params: dict[str, Any]
        raw_params = data.get("params")
        if isinstance(raw_params, dict):
            params = dict(raw_params)
        else:
            params = {}

        if isinstance(parameters, dict):
            nested_params = parameters.get("params")
            if isinstance(nested_params, dict):
                params.update(nested_params)
            for key, value in parameters.items():
                if key != "params":
                    params.setdefault(key, value)

        query_type = data.get("query_type")
        if isinstance(query_type, str) and query_type.strip():
            query_type = query_type.strip().lower()
            if query_type not in KNOWN_QUERY_TYPES:
                inferred_type, inferred_params = _infer_query_type(
                    query_type,
                    principal_id=principal_id,
                )
                query_type = inferred_type
                for key, value in inferred_params.items():
                    params.setdefault(key, value)

        if not isinstance(query_type, str) or not query_type.strip():
            query_candidate: str | None = None
            if isinstance(data.get("query"), str):
                query_candidate = data["query"]
            elif isinstance(parameters, dict):
                candidate = parameters.get("query")
                if isinstance(candidate, str):
                    query_candidate = candidate
                else:
                    candidate_type = parameters.get("query_type") or parameters.get("queryType")
                    if isinstance(candidate_type, str):
                        query_type = candidate_type

            if not isinstance(query_type, str) or not query_type.strip():
                if isinstance(query_candidate, str):
                    inferred_type, inferred_params = _infer_query_type(
                        query_candidate,
                        principal_id=principal_id,
                    )
                    query_type = inferred_type
                    for key, value in inferred_params.items():
                        params.setdefault(key, value)
                else:
                    query_type = "balances"
                    params.setdefault("principal_id", principal_id)

        data["query_type"] = query_type.strip().lower()
        data["params"] = params

    return data


def parse_intent_from_json(principal_id: str, json_str: str) -> ActionIntent | str:
    """Parse a model-produced JSON action into a typed intent."""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        return f"Invalid JSON: {exc}"

    if not isinstance(data, dict):
        return "Action payload must be a JSON object"

    data = _normalize_payload(principal_id, data)
    action_type_raw = str(data.get("action_type", "")).strip().lower()
    reasoning = str(data.get("reasoning", ""))

    if action_type_raw == ActionType.NOOP.value:
        return NoopIntent(principal_id, reasoning)

    if action_type_raw == ActionType.READ_ARTIFACT.value:
        artifact_id = data.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            return "read_artifact requires 'artifact_id' (string)"
        return ReadArtifactIntent(principal_id, artifact_id, reasoning)

    if action_type_raw == ActionType.WRITE_ARTIFACT.value:
        artifact_id = data.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            return "write_artifact requires 'artifact_id' (string)"
        artifact_type = str(data.get("artifact_type", "generic"))
        content = data.get("content", "")
        if not isinstance(content, str):
            content = json.dumps(content)
        executable = bool(data.get("executable", False))
        code = str(data.get("code", ""))
        if executable and not code:
            return "write_artifact executable=true requires 'code'"
        read_price = int(data.get("read_price", 0) or 0)
        invoke_price = int(data.get("invoke_price", data.get("price", 0)) or 0)
        access_contract_id = data.get("access_contract_id")
        if access_contract_id is not None and not isinstance(access_contract_id, str):
            return "access_contract_id must be a string or null"
        metadata = data.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            return "metadata must be a dict or null"
        interface = data.get("interface")
        if interface is not None and not isinstance(interface, dict):
            return "interface must be a dict or null"
        has_standing = bool(data.get("has_standing", False))
        has_loop = bool(data.get("has_loop", False))
        capabilities = data.get("capabilities")
        if capabilities is None:
            capabilities_list: list[str] = []
        elif isinstance(capabilities, list):
            capabilities_list = [str(item) for item in capabilities]
        else:
            return "capabilities must be a list"

        return WriteArtifactIntent(
            principal_id,
            artifact_id,
            artifact_type,
            content,
            executable=executable,
            code=code,
            read_price=read_price,
            invoke_price=invoke_price,
            access_contract_id=access_contract_id,
            metadata=metadata,
            interface=interface,
            has_standing=has_standing,
            has_loop=has_loop,
            capabilities=capabilities_list,
            reasoning=reasoning,
        )

    if action_type_raw == ActionType.EDIT_ARTIFACT.value:
        artifact_id = data.get("artifact_id")
        old_string = data.get("old_string")
        new_string = data.get("new_string")
        if not isinstance(artifact_id, str) or not artifact_id:
            return "edit_artifact requires 'artifact_id'"
        if not isinstance(old_string, str):
            return "edit_artifact requires 'old_string'"
        if not isinstance(new_string, str):
            return "edit_artifact requires 'new_string'"
        if old_string == new_string:
            return "edit_artifact old_string and new_string must differ"
        return EditArtifactIntent(principal_id, artifact_id, old_string, new_string, reasoning)

    if action_type_raw == ActionType.INVOKE_ARTIFACT.value:
        artifact_id = data.get("artifact_id")
        method = data.get("method")
        args = data.get("args", [])
        if not isinstance(artifact_id, str) or not artifact_id:
            return "invoke_artifact requires 'artifact_id'"
        if not isinstance(method, str) or not method:
            return "invoke_artifact requires 'method'"
        if not isinstance(args, list):
            return "invoke_artifact 'args' must be a list"
        return InvokeArtifactIntent(principal_id, artifact_id, method, args, reasoning)

    if action_type_raw == ActionType.DELETE_ARTIFACT.value:
        artifact_id = data.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            return "delete_artifact requires 'artifact_id'"
        return DeleteArtifactIntent(principal_id, artifact_id, reasoning)

    if action_type_raw == ActionType.QUERY_KERNEL.value:
        query_type = data.get("query_type")
        params = data.get("params", {})
        if not isinstance(query_type, str) or not query_type:
            return "query_kernel requires 'query_type'"
        if not isinstance(params, dict):
            return "query_kernel params must be a dict"
        return QueryKernelIntent(principal_id, query_type, params, reasoning)

    if action_type_raw == ActionType.SUBSCRIBE_ARTIFACT.value:
        artifact_id = data.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            return "subscribe_artifact requires 'artifact_id'"
        return SubscribeArtifactIntent(principal_id, artifact_id, reasoning)

    if action_type_raw == ActionType.UNSUBSCRIBE_ARTIFACT.value:
        artifact_id = data.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            return "unsubscribe_artifact requires 'artifact_id'"
        return UnsubscribeArtifactIntent(principal_id, artifact_id, reasoning)

    if action_type_raw == ActionType.TRANSFER.value:
        recipient_id = data.get("recipient_id")
        amount = _coerce_int(data.get("amount"))
        memo = data.get("memo")
        if not isinstance(recipient_id, str) or not recipient_id:
            return "transfer requires 'recipient_id'"
        if amount is None or amount <= 0:
            return "transfer requires positive integer 'amount'"
        if memo is not None and not isinstance(memo, str):
            return "transfer memo must be string or null"
        return TransferIntent(principal_id, recipient_id, amount, memo, reasoning)

    if action_type_raw == ActionType.MINT.value:
        recipient_id = data.get("recipient_id")
        amount = _coerce_int(data.get("amount"))
        reason = data.get("reason")
        if not isinstance(recipient_id, str) or not recipient_id:
            return "mint requires 'recipient_id'"
        if amount is None or amount <= 0:
            return "mint requires positive integer 'amount'"
        if not isinstance(reason, str) or not reason:
            return "mint requires 'reason'"
        return MintIntent(principal_id, recipient_id, amount, reason, reasoning)

    if action_type_raw == ActionType.SUBMIT_TO_MINT.value:
        artifact_id = data.get("artifact_id")
        bid = _coerce_int(data.get("bid"))
        if not isinstance(artifact_id, str) or not artifact_id:
            return "submit_to_mint requires 'artifact_id'"
        if bid is None or bid <= 0:
            return "submit_to_mint requires positive integer 'bid'"
        return SubmitToMintIntent(principal_id, artifact_id, bid, reasoning)

    if action_type_raw == ActionType.UPDATE_METADATA.value:
        artifact_id = data.get("artifact_id")
        key = data.get("key")
        if not isinstance(artifact_id, str) or not artifact_id:
            return "update_metadata requires 'artifact_id'"
        if not isinstance(key, str) or not key:
            return "update_metadata requires 'key'"
        return UpdateMetadataIntent(principal_id, artifact_id, key, data.get("value"), reasoning)

    return (
        f"Unknown action_type: {action_type_raw}. "
        "Valid actions: noop, read_artifact, write_artifact, edit_artifact, "
        "delete_artifact, invoke_artifact, query_kernel, subscribe_artifact, "
        "unsubscribe_artifact, transfer, mint, submit_to_mint, update_metadata"
    )
