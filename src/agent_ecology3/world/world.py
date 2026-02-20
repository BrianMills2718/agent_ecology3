"""World kernel orchestration for Agent Ecology 3."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import AppConfig
from .action_executor import ActionExecutor
from .actions import ActionIntent, ActionResult, InvokeArtifactIntent, QueryKernelIntent, parse_intent_from_json
from .artifacts import Artifact, ArtifactStore
from .contracts import (
    KERNEL_CONTRACT_PRIVATE,
    KERNEL_CONTRACT_SELF_OWNED,
    ContractEngine,
)
from .delegation import DelegationManager
from .executor import get_executor
from .ledger import Ledger
from .logger import EventLogger, SummarySnapshot
from .mint import MintAuction, MintScorer
from .queries import KernelQueryHandler
from .rates import RateTracker


class KernelStateRouter:
    """Read-only kernel view exposed to executable artifacts."""

    def __init__(self, world: "World") -> None:
        self._world = world

    def for_principal(self, principal_id: str) -> "KernelStateView":
        return KernelStateView(self._world, principal_id)


class KernelStateView:
    """Principal-scoped read-only state view."""

    def __init__(self, world: "World", principal_id: str) -> None:
        self._world = world
        self._principal_id = principal_id

    def read_artifact(self, artifact_id: str, _caller_id: str | None = None) -> str | None:
        artifact = self._world.artifacts.get(artifact_id)
        if artifact is None or artifact.deleted:
            return None
        # Preserve kernel safety by routing through normal action path.
        result = self._world.execute_action_data(
            self._principal_id,
            {"action_type": "read_artifact", "artifact_id": artifact_id},
            increment_event=False,
        )
        if not result.success or not result.data:
            return None
        payload = result.data.get("artifact")
        if isinstance(payload, dict):
            content = payload.get("content")
            if isinstance(content, str):
                return content
        return None

    def list_artifacts(self, owner: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if owner:
            params["owner"] = owner
        result = self._world.query_handler.execute("artifacts", params)
        if not result.get("success"):
            return []
        artifacts = result.get("results")
        if not isinstance(artifacts, list):
            return []
        return [item for item in artifacts if isinstance(item, dict)]

    def get_balance(self) -> int:
        return self._world.ledger.get_scrip(self._principal_id)

    def get_resources(self) -> dict[str, Any]:
        return {
            "llm_budget": self._world.ledger.get_llm_budget(self._principal_id),
            "disk_quota": self._world.get_disk_quota(self._principal_id),
            "disk_used": self._world.artifacts.get_owner_usage(self._principal_id),
            "disk_available": self._world.get_available_disk(self._principal_id),
            "llm_calls_remaining": self._world.ledger.get_resource_remaining(self._principal_id, "llm_calls"),
            "llm_tokens_remaining": self._world.ledger.get_resource_remaining(self._principal_id, "llm_tokens"),
            "cpu_seconds_remaining": self._world.ledger.get_resource_remaining(self._principal_id, "cpu_seconds"),
        }

    def recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._world.logger.read_recent(limit)


class KernelActionRouter:
    """Action router exposed to executable artifacts."""

    def __init__(self, world: "World") -> None:
        self._world = world

    def for_principal(self, principal_id: str) -> "KernelActions":
        return KernelActions(self._world, principal_id)


class KernelActions:
    """Principal-scoped mutation API for executable artifacts."""

    def __init__(self, world: "World", principal_id: str) -> None:
        self._world = world
        self._principal_id = principal_id

    def run_action(self, action: dict[str, Any] | str) -> dict[str, Any]:
        result = self._world.execute_action_data(self._principal_id, action)
        return result.to_dict()

    def query_kernel(self, query_type: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        intent = QueryKernelIntent(self._principal_id, query_type, params or {})
        result = self._world.execute_intent(intent)
        return result.to_dict()

    def write_artifact(
        self,
        artifact_id: str,
        content: str,
        artifact_type: str = "generic",
        *,
        executable: bool = False,
        code: str = "",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "action_type": "write_artifact",
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "content": content,
            "executable": executable,
            "code": code,
        }
        return self.run_action(payload)

    def invoke_artifact(self, artifact_id: str, method: str = "run", args: list[Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "action_type": "invoke_artifact",
            "artifact_id": artifact_id,
            "method": method,
            "args": args or [],
        }
        return self.run_action(payload)


class World:
    """Kernel runtime state and action execution orchestration."""

    def __init__(self, config: AppConfig, run_id: str | None = None) -> None:
        self.config = config
        self.run_id = run_id or datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")
        self.event_number = 0
        self.max_invoke_depth = 6
        self.frozen_agents: set[str] = set()
        self.disk_quotas: dict[str, int] = {}
        self.installed_libraries: dict[str, list[dict[str, Any]]] = {}

        self.rate_tracker = RateTracker(window_seconds=config.resources.rate_window_seconds)
        self.rate_tracker.configure_limit("llm_calls", config.resources.rate_limits.llm_calls_per_window)
        self.rate_tracker.configure_limit("llm_tokens", config.resources.rate_limits.llm_tokens_per_window)
        self.rate_tracker.configure_limit("cpu_seconds", config.resources.rate_limits.cpu_seconds_per_window)

        self.ledger = Ledger(self.rate_tracker)
        self.artifacts = ArtifactStore()
        self.logger = EventLogger(
            logs_dir=config.logging.logs_dir,
            run_id=self.run_id,
            event_file_name=config.logging.event_file_name,
            summary_file_name=config.logging.summary_file_name,
        )

        self.contract_engine = ContractEngine(
            self.artifacts,
            self.ledger,
            default_when_missing=config.contracts.default_when_missing,
        )
        self.delegation_manager = DelegationManager()
        self.executor = get_executor(timeout_seconds=max(3, config.llm.timeout_seconds))
        self.query_handler = KernelQueryHandler(self)
        self.action_executor = ActionExecutor(self)

        self.kernel_state = KernelStateRouter(self)
        self.kernel_actions = KernelActionRouter(self)
        self.kernel_services: dict[str, dict[str, Any]] = {}

        self.mint_auction: MintAuction | None = None

        self._bootstrap_principals()
        self._bootstrap_kernel_services()
        self._bootstrap_loop_artifacts()
        self._bootstrap_mint_systems()

        self.logger.log(
            "world_initialized",
            {
                "event_number": self.event_number,
                "run_id": self.run_id,
                "principal_count": len(self.principal_ids),
                "artifact_count": len(self.artifacts.artifacts),
            },
        )

    @property
    def principal_ids(self) -> list[str]:
        return sorted(self.ledger.get_all_scrip().keys())

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _bootstrap_principals(self) -> None:
        for idx in range(self.config.principals.count):
            principal_id = f"{self.config.principals.id_prefix}{idx + 1}"
            self.ledger.create_principal(
                principal_id,
                starting_scrip=self.config.principals.starting_scrip,
                starting_resources={"llm_budget": self.config.principals.starting_llm_budget},
            )
            self.set_disk_quota(principal_id, self.config.principals.starting_disk_quota_bytes)
            self.installed_libraries[principal_id] = []

            # Each principal has a private mutable profile artifact.
            self.artifacts.write(
                principal_id,
                "agent_profile",
                json.dumps({"subscribed_artifacts": [], "context_sections": {}}, ensure_ascii=True),
                created_by=principal_id,
                owner=principal_id,
                access_contract_id=KERNEL_CONTRACT_SELF_OWNED,
                has_standing=True,
            )

    def _bootstrap_kernel_services(self) -> None:
        def kernel_act_run(args: list[Any], principal_id: str) -> dict[str, Any]:
            if not args:
                return {
                    "success": False,
                    "error": "kernel_act requires one action payload argument",
                    "error_code": "missing_argument",
                }
            payload = args[0]
            result = self.execute_action_data(principal_id, payload)
            return result.to_dict()

        def kernel_delegation_run(args: list[Any], principal_id: str) -> dict[str, Any]:
            if not args:
                return {
                    "success": True,
                    "delegations": self.delegation_manager.as_dict(principal_id),
                }
            cmd = args[0]
            if not isinstance(cmd, str):
                return {"success": False, "error": "first arg must be command string"}
            command = cmd.lower().strip()
            if command == "grant":
                if len(args) < 2 or not isinstance(args[1], str):
                    return {"success": False, "error": "grant requires charger_id"}
                charger_id = args[1]
                kwargs: dict[str, Any] = {}
                if len(args) > 2 and isinstance(args[2], dict):
                    kwargs = args[2]
                self.delegation_manager.grant(principal_id, charger_id, **kwargs)
                return {"success": True, "message": "delegation granted", "charger_id": charger_id}
            if command == "revoke":
                if len(args) < 2 or not isinstance(args[1], str):
                    return {"success": False, "error": "revoke requires charger_id"}
                charger_id = args[1]
                ok = self.delegation_manager.revoke(principal_id, charger_id)
                return {"success": ok, "message": "delegation revoked" if ok else "delegation not found"}
            if command in {"list", "status"}:
                return {"success": True, "delegations": self.delegation_manager.as_dict(principal_id)}
            return {"success": False, "error": f"unknown command '{command}'"}

        def kernel_mint_run(args: list[Any], principal_id: str) -> dict[str, Any]:
            if self.mint_auction is None:
                return {"success": False, "error": "mint disabled", "error_code": "not_enabled"}
            if not args:
                return {"success": True, "status": self.mint_auction.status()}
            cmd = args[0]
            if not isinstance(cmd, str):
                return {"success": False, "error": "first arg must be command string"}
            command = cmd.lower().strip()
            if command == "status":
                return {
                    "success": True,
                    "status": self.mint_auction.status(),
                    "submissions": self.mint_auction.get_submissions(),
                    "history": self.mint_auction.get_history(limit=20),
                }
            if command == "update":
                return {"success": True, "result": self.mint_auction.update()}
            if command == "submit":
                if len(args) < 3:
                    return {"success": False, "error": "submit requires artifact_id and bid"}
                artifact_id = args[1]
                bid = args[2]
                if not isinstance(artifact_id, str) or not isinstance(bid, int):
                    return {"success": False, "error": "invalid submit args"}
                try:
                    submission_id = self.mint_auction.submit(principal_id, artifact_id, bid)
                except ValueError as exc:
                    return {"success": False, "error": str(exc), "error_code": "invalid_submission"}
                return {"success": True, "submission_id": submission_id}
            if command == "cancel":
                if len(args) < 2 or not isinstance(args[1], str):
                    return {"success": False, "error": "cancel requires submission_id"}
                ok = self.mint_auction.cancel(principal_id, args[1])
                return {"success": ok, "message": "cancelled" if ok else "not_found"}
            return {"success": False, "error": f"unknown command '{command}'"}

        def kernel_time_run(args: list[Any], principal_id: str) -> dict[str, Any]:
            _ = args, principal_id
            return {
                "success": True,
                "now": self.now_iso(),
                "event_number": self.event_number,
            }

        self.kernel_services = {
            "kernel_act": {
                "description": "Execute kernel action payloads",
                "methods": {"run": kernel_act_run},
            },
            "kernel_delegation": {
                "description": "Manage charge delegation grants",
                "methods": {"run": kernel_delegation_run},
            },
            "kernel_mint": {
                "description": "Inspect and submit to mint auction",
                "methods": {"run": kernel_mint_run, "status": kernel_mint_run, "update": kernel_mint_run},
            },
            "kernel_time": {
                "description": "Return current simulation clock",
                "methods": {"run": kernel_time_run},
            },
        }

        for service_id, service in self.kernel_services.items():
            self.artifacts.write(
                service_id,
                "kernel_service",
                str(service.get("description", service_id)),
                created_by="SYSTEM_KERNEL",
                owner="SYSTEM_KERNEL",
                access_contract_id=KERNEL_CONTRACT_PRIVATE,
            )
            artifact = self.artifacts.get(service_id)
            if artifact is not None:
                artifact.kernel_protected = True

    def _default_loop_code(self, principal_id: str, slot: int) -> str:
        scratch_id = f"{principal_id}_scratch"
        principal_prefix = self.config.principals.id_prefix
        principal_count = max(1, self.config.principals.count)
        return f'''import json
import time


def _extract_json(text):
    if not isinstance(text, str):
        return None
    start = text.find("{{")
    end = text.rfind("}}")
    if start < 0 or end < start:
        return None
    try:
        return json.loads(text[start:end+2])
    except Exception:
        return None


def _neighbor_principal():
    if {principal_count} <= 1:
        return "{principal_id}"
    turn = int(time.time()) + {slot}
    idx = (turn % {principal_count}) + 1
    candidate = "{principal_prefix}" + str(idx)
    if candidate == "{principal_id}":
        idx = ((idx % {principal_count}) + 1)
        candidate = "{principal_prefix}" + str(idx)
    return candidate


def _artifact_ids(state_snapshot):
    artifact_ids = set()
    if not isinstance(state_snapshot, dict):
        return artifact_ids
    artifacts = state_snapshot.get("artifacts")
    if not isinstance(artifacts, list):
        return artifact_ids
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        artifact_id = item.get("id")
        if isinstance(artifact_id, str) and artifact_id:
            artifact_ids.add(artifact_id)
    return artifact_ids


def _pick_read_target(state_snapshot):
    own_prefix = "{principal_id}_"
    if not isinstance(state_snapshot, dict):
        return None
    artifacts = state_snapshot.get("artifacts")
    if not isinstance(artifacts, list):
        return None
    preferred = None
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        artifact_id = item.get("id")
        if not isinstance(artifact_id, str) or not artifact_id:
            continue
        if artifact_id.count("_") < 2:
            continue
        if artifact_id.startswith(own_prefix):
            continue
        if artifact_id.endswith("_scratch"):
            return artifact_id
        if preferred is None:
            preferred = artifact_id
    return preferred


def _artifact_exists(artifact_id):
    if "kernel_state" not in globals():
        return False
    try:
        return kernel_state.read_artifact(artifact_id) is not None
    except Exception:
        return False


def _fallback_action(state_snapshot):
    existing = _artifact_ids(state_snapshot)
    own_scratch_exists = "{scratch_id}" in existing or _artifact_exists("{scratch_id}")
    read_target = _pick_read_target(state_snapshot)
    balance = 0
    if isinstance(state_snapshot, dict):
        raw_balance = state_snapshot.get("balance")
        if isinstance(raw_balance, int):
            balance = raw_balance
    neighbor = _neighbor_principal()
    neighbor_scratch = neighbor + "_scratch"
    if _artifact_exists(neighbor_scratch):
        read_target = neighbor_scratch
    turn = int(time.time()) + {slot}
    phase = turn % 4
    if phase == 0 or not own_scratch_exists:
        return {{
            "action_type": "write_artifact",
            "artifact_id": "{scratch_id}",
            "artifact_type": "note",
            "content": "heartbeat from {principal_id} turn " + str(turn),
        }}
    if phase == 1:
        if read_target is None:
            return {{
                "action_type": "write_artifact",
                "artifact_id": "{scratch_id}",
                "artifact_type": "note",
                "content": "state snapshot for {principal_id} turn " + str(turn),
            }}
        return {{
            "action_type": "read_artifact",
            "artifact_id": read_target,
        }}
    if phase == 2:
        if balance <= 1:
            return {{
                "action_type": "write_artifact",
                "artifact_id": "{scratch_id}",
                "artifact_type": "note",
                "content": "low balance hold for {principal_id} turn " + str(turn),
            }}
        return {{
            "action_type": "transfer",
            "recipient_id": neighbor,
            "amount": 1,
            "memo": "coordination pulse",
        }}
    if not own_scratch_exists or balance < 1:
        return {{
            "action_type": "write_artifact",
            "artifact_id": "{scratch_id}",
            "artifact_type": "note",
            "content": "mint prep from {principal_id} turn " + str(turn),
        }}
    return {{
        "action_type": "submit_to_mint",
        "artifact_id": "{scratch_id}",
        "bid": 1,
    }}


def _should_force_explore(decision):
    if ((int(time.time()) + {slot}) % 5) == 0:
        return True
    if not isinstance(decision, dict):
        return True
    action = decision.get("action_type")
    if not isinstance(action, str):
        action = decision.get("action")
    action = str(action or "").strip().lower()
    if action in ("", "noop"):
        return True
    if action == "query_kernel":
        return ((int(time.time()) + {slot}) % 3) == 0
    return False


def run():
    state_snapshot = {{}}
    if "kernel_state" in globals():
        try:
            state_snapshot = {{
                "balance": kernel_state.get_balance(),
                "resources": kernel_state.get_resources(),
                "artifacts": kernel_state.list_artifacts(limit=12),
            }}
        except Exception:
            state_snapshot = {{}}

    prompt = (
        "You are agent {principal_id} in an economy simulation. "
        "Return exactly one JSON action object and never use noop. "
        "Valid action_type values include write_artifact, read_artifact, transfer, "
        "submit_to_mint, query_kernel. "
        "Do not invoke artifacts directly. "
        "For query_kernel you must include query_type and params object. "
        "Do not modify *_loop artifacts. "
        "When writing artifacts, use ids prefixed with {principal_id}_. "
        "Prefer interaction and production actions over status checks."
    )

    decision = None
    if "_syscall_llm" in globals():
        llm_result = _syscall_llm(
            model="{self.config.llm.default_model}",
            messages=[
                {{"role": "system", "content": "Return only one valid JSON action object. No prose."}},
                {{"role": "user", "content": prompt + "\\nState:\\n" + json.dumps(state_snapshot)}},
            ],
        )
        if llm_result.get("success"):
            decision = _extract_json(llm_result.get("content", ""))

    if _should_force_explore(decision):
        decision = _fallback_action(state_snapshot)

    result = invoke("kernel_act", decision)
    if not result.get("success"):
        fallback = _fallback_action(state_snapshot)
        recovery = invoke("kernel_act", fallback)
        return {{"decision": decision, "fallback": fallback, "result": recovery}}
    return {{"decision": decision, "result": result}}
'''

    def _bootstrap_loop_artifacts(self) -> None:
        for idx, principal_id in enumerate(self.principal_ids, start=1):
            loop_id = f"{principal_id}_loop"
            self.artifacts.write(
                loop_id,
                "agent_loop",
                f"Autonomous loop artifact for {principal_id}",
                created_by="SYSTEM_KERNEL",
                owner=principal_id,
                executable=True,
                code=self._default_loop_code(principal_id, idx),
                access_contract_id=KERNEL_CONTRACT_PRIVATE,
                has_loop=True,
                capabilities=["can_call_llm"] if self.config.llm.enable_bootstrap_loop_llm else [],
            )
            artifact = self.artifacts.get(loop_id)
            if artifact is not None:
                artifact.kernel_protected = True

    def _bootstrap_mint_systems(self) -> None:
        if self.config.mint.enabled:
            scorer = MintScorer(
                model=self.config.llm.default_model,
                timeout_seconds=self.config.llm.timeout_seconds,
            )
            self.mint_auction = MintAuction(
                ledger=self.ledger,
                artifacts=self.artifacts,
                logger=self.logger,
                event_number_getter=lambda: self.event_number,
                minimum_bid=self.config.mint.minimum_bid,
                first_auction_delay_seconds=self.config.mint.first_auction_delay_seconds,
                bidding_window_seconds=self.config.mint.bidding_window_seconds,
                period_seconds=self.config.mint.period_seconds,
                mint_ratio=self.config.mint.mint_ratio,
                scorer=scorer,
            )

    def set_disk_quota(self, principal_id: str, quota_bytes: int) -> None:
        self.disk_quotas[principal_id] = max(0, int(quota_bytes))

    def get_disk_quota(self, principal_id: str) -> int:
        return self.disk_quotas.get(principal_id, self.config.principals.starting_disk_quota_bytes)

    def get_available_disk(self, principal_id: str) -> int:
        used = self.artifacts.get_owner_usage(principal_id)
        quota = self.get_disk_quota(principal_id)
        return max(0, quota - used)

    def get_principal_quotas(self, principal_id: str) -> dict[str, dict[str, float | int]]:
        return {
            "disk": {
                "quota": self.get_disk_quota(principal_id),
                "used": self.artifacts.get_owner_usage(principal_id),
                "available": self.get_available_disk(principal_id),
            },
            "llm_budget": {
                "balance": self.ledger.get_llm_budget(principal_id),
            },
            "llm_calls": {
                "limit": self.rate_tracker.get_limit("llm_calls"),
                "remaining": self.ledger.get_resource_remaining(principal_id, "llm_calls"),
            },
            "llm_tokens": {
                "limit": self.rate_tracker.get_limit("llm_tokens"),
                "remaining": self.ledger.get_resource_remaining(principal_id, "llm_tokens"),
            },
            "cpu_seconds": {
                "limit": self.rate_tracker.get_limit("cpu_seconds"),
                "remaining": self.ledger.get_resource_remaining(principal_id, "cpu_seconds"),
            },
        }

    def is_agent_frozen(self, agent_id: str) -> bool:
        return agent_id in self.frozen_agents

    def freeze_agent(self, agent_id: str) -> None:
        self.frozen_agents.add(agent_id)

    def unfreeze_agent(self, agent_id: str) -> None:
        self.frozen_agents.discard(agent_id)

    def execute_intent(self, intent: ActionIntent, *, increment_event: bool = True) -> ActionResult:
        if increment_event:
            self.event_number += 1
        return self.action_executor.execute(intent)

    def execute_action_data(
        self,
        principal_id: str,
        payload: dict[str, Any] | str,
        *,
        increment_event: bool = True,
    ) -> ActionResult:
        json_payload = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=True)
        parsed = parse_intent_from_json(principal_id, json_payload)
        if isinstance(parsed, str):
            return ActionResult(
                success=False,
                message=parsed,
                error_code="invalid_action",
                error_category="validation",
                retriable=True,
            )
        return self.execute_intent(parsed, increment_event=increment_event)

    def invoke_from_executor(
        self,
        *,
        caller_id: str,
        target_id: str,
        method: str,
        args: list[Any],
        current_depth: int,
        max_depth: int,
    ) -> dict[str, Any]:
        intent = InvokeArtifactIntent(caller_id, target_id, method, args)
        setattr(intent, "_invoke_depth", current_depth)
        setattr(intent, "_max_invoke_depth", max_depth)
        self.event_number += 1
        result = self.action_executor._invoke(intent)
        payload = result.to_dict()
        if result.success:
            payload.setdefault("success", True)
            return payload
        payload.setdefault("success", False)
        payload.setdefault("error", result.message)
        return payload

    def _estimate_tokens(self, messages: list[dict[str, Any]]) -> int:
        rough_chars = 0
        for message in messages:
            content = message.get("content", "")
            rough_chars += len(str(content))
        return max(20, rough_chars // 4)

    def call_llm_as_syscall(
        self,
        *,
        payer_id: str,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if self.config.llm.allowed_models and model not in self.config.llm.allowed_models:
            return {
                "success": False,
                "error": f"model '{model}' is not allowed",
                "error_code": "model_not_allowed",
            }

        # Preflight reservation values; settled to actuals after call.
        estimated_tokens = self._estimate_tokens(messages)
        estimated_cost = max(0.0002, estimated_tokens / 1000.0 * 0.003)

        if not self.ledger.can_afford_llm_call(payer_id, estimated_cost):
            return {
                "success": False,
                "error": "insufficient llm_budget",
                "error_code": "insufficient_budget",
                "estimated_cost": estimated_cost,
                "budget": self.ledger.get_llm_budget(payer_id),
            }

        # Reserve expected budget before calling provider; reconcile after response.
        if not self.ledger.spend_resource(payer_id, "llm_budget", estimated_cost):
            return {
                "success": False,
                "error": "failed to reserve llm_budget",
                "error_code": "insufficient_budget",
            }

        if not self.ledger.consume_resource(payer_id, "llm_calls", 1.0):
            self.ledger.credit_resource(payer_id, "llm_budget", estimated_cost)
            return {
                "success": False,
                "error": "llm_calls rate limit exceeded",
                "error_code": "rate_limited",
                "retry_after_seconds": self.rate_tracker.time_until_capacity(payer_id, "llm_calls", 1.0),
            }

        if not self.ledger.consume_resource(payer_id, "llm_tokens", float(estimated_tokens)):
            self.ledger.refund_resource_usage(payer_id, "llm_calls", 1.0)
            self.ledger.credit_resource(payer_id, "llm_budget", estimated_cost)
            return {
                "success": False,
                "error": "llm_tokens rate limit exceeded",
                "error_code": "rate_limited",
                "retry_after_seconds": self.rate_tracker.time_until_capacity(
                    payer_id, "llm_tokens", float(estimated_tokens)
                ),
            }

        start = time.perf_counter()
        try:
            try:
                from llm_client import call_llm
            except Exception as exc:  # pragma: no cover - optional dependency fallback
                raise RuntimeError(f"llm_client import failed: {exc}") from exc

            trace_id = f"ae3/{self.run_id}/event_{self.event_number}/payer/{payer_id}"
            llm_result = call_llm(
                model=model,
                messages=messages,
                tools=tools,
                timeout=self.config.llm.timeout_seconds,
                task="agent_ecology3_syscall",
                trace_id=trace_id,
                max_budget=0.0,
            )
            content = llm_result.content or ""
            usage_raw = llm_result.usage if isinstance(llm_result.usage, dict) else {}
            prompt_tokens = int(usage_raw.get("prompt_tokens", usage_raw.get("input_tokens", 0)) or 0)
            completion_tokens = int(usage_raw.get("completion_tokens", usage_raw.get("output_tokens", 0)) or 0)
            actual_tokens = int(usage_raw.get("total_tokens", prompt_tokens + completion_tokens) or 0)

            cache_hit = bool(getattr(llm_result, "cache_hit", False))
            actual_cost = float(getattr(llm_result, "marginal_cost", llm_result.cost) or 0.0)
            cost_source = str(getattr(llm_result, "cost_source", "unknown"))
            billing_mode = str(getattr(llm_result, "billing_mode", "unknown"))

            if cache_hit:
                actual_tokens = 0
                actual_cost = 0.0
                self.ledger.refund_resource_usage(payer_id, "llm_calls", 1.0)

            # Reconcile token reservation to measured tokens (or zero on cache hit).
            if actual_tokens < estimated_tokens:
                self.ledger.refund_resource_usage(
                    payer_id,
                    "llm_tokens",
                    float(estimated_tokens - actual_tokens),
                )
            elif actual_tokens > estimated_tokens:
                extra_tokens = float(actual_tokens - estimated_tokens)
                extra_ok = self.ledger.consume_resource(payer_id, "llm_tokens", extra_tokens)
                if not extra_ok:
                    self.logger.log(
                        "llm_syscall_token_overage",
                        {
                            "event_number": self.event_number,
                            "payer_id": payer_id,
                            "model": model,
                            "estimated_tokens": estimated_tokens,
                            "actual_tokens": actual_tokens,
                            "extra_tokens": extra_tokens,
                        },
                    )

            # Reconcile budget reservation against measured marginal cost.
            charged_cost = 0.0
            undercharged_cost = 0.0
            if actual_cost <= estimated_cost:
                refund = estimated_cost - actual_cost
                if refund > 0:
                    self.ledger.credit_resource(payer_id, "llm_budget", refund)
                charged_cost = actual_cost
            else:
                extra_cost = actual_cost - estimated_cost
                extra_available = max(0.0, self.ledger.get_llm_budget(payer_id))
                charge_extra = min(extra_cost, extra_available)
                if charge_extra > 0:
                    self.ledger.spend_resource(payer_id, "llm_budget", charge_extra)
                charged_cost = estimated_cost + charge_extra
                undercharged_cost = max(0.0, extra_cost - charge_extra)

            duration_ms = (time.perf_counter() - start) * 1000
            usage: dict[str, int] = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": actual_tokens,
            }
            self.logger.log(
                "llm_syscall",
                {
                    "event_number": self.event_number,
                    "payer_id": payer_id,
                    "model": model,
                    "actual_cost": actual_cost,
                    "charged_cost": charged_cost,
                    "cost_source": cost_source,
                    "billing_mode": billing_mode,
                    "cache_hit": cache_hit,
                    "undercharged_cost": undercharged_cost,
                    "duration_ms": duration_ms,
                    "tokens": usage,
                },
            )
            return {
                "success": True,
                "content": content,
                "model": model,
                "cost": actual_cost,
                "charged_cost": charged_cost,
                "cost_source": cost_source,
                "billing_mode": billing_mode,
                "cache_hit": cache_hit,
                "undercharged_cost": undercharged_cost,
                "usage": usage,
                "duration_ms": duration_ms,
            }
        except Exception as exc:
            # Undo reservations if call failed.
            self.ledger.refund_resource_usage(payer_id, "llm_calls", 1.0)
            self.ledger.refund_resource_usage(payer_id, "llm_tokens", float(estimated_tokens))
            self.ledger.credit_resource(payer_id, "llm_budget", estimated_cost)
            duration_ms = (time.perf_counter() - start) * 1000
            self.logger.log(
                "llm_syscall_error",
                {
                    "event_number": self.event_number,
                    "payer_id": payer_id,
                    "model": model,
                    "error": str(exc),
                    "duration_ms": duration_ms,
                },
            )
            return {
                "success": False,
                "error": f"llm call failed: {exc}",
                "error_code": "llm_error",
                "duration_ms": duration_ms,
            }

    def tick(self) -> None:
        if self.mint_auction is not None:
            _ = self.mint_auction.update()

    def log_summary_snapshot(self) -> None:
        snapshot = SummarySnapshot(
            timestamp=self.now_iso(),
            event_number=self.event_number,
            action_count=len([e for e in self.logger.read_recent(500) if e.get("event_type") == "action"]),
            principal_count=len(self.principal_ids),
            artifact_count=len([a for a in self.artifacts.artifacts.values() if not a.deleted]),
            total_scrip=sum(self.ledger.get_all_scrip().values()),
        )
        self.logger.log_summary(snapshot)

    def get_state_summary(self, event_limit: int = 100) -> dict[str, Any]:
        artifacts = [a.to_dict(include_code=False) for a in self.artifacts.artifacts.values() if not a.deleted]
        balances = self.ledger.get_all_balances()
        quotas = {pid: self.get_principal_quotas(pid) for pid in self.principal_ids}

        return {
            "run_id": self.run_id,
            "event_number": self.event_number,
            "principal_count": len(self.principal_ids),
            "artifact_count": len(artifacts),
            "principals": self.principal_ids,
            "balances": balances,
            "quotas": quotas,
            "artifacts": artifacts,
            "mint": {
                "enabled": self.mint_auction is not None,
                "status": self.mint_auction.status() if self.mint_auction else {"phase": "disabled"},
            },
            "events": self.logger.read_recent(event_limit),
            "frozen": sorted(self.frozen_agents),
            "installed_libraries": self.installed_libraries,
            "log_path": str(Path(self.logger.output_path)),
        }
