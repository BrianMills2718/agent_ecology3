"""World kernel orchestration for Agent Ecology 3."""

from __future__ import annotations

import json
import sys
import time
from collections import deque
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

ROLE_PROFILES: tuple[dict[str, str], ...] = (
    {
        "name": "market_maker",
        "specialization": "resource pricing and bilateral trade clearing",
        "focus": "broker transfers and keep markets liquid",
    },
    {
        "name": "toolsmith",
        "specialization": "reusable utilities and service artifacts",
        "focus": "ship useful artifacts and attract downstream usage",
    },
    {
        "name": "auditor",
        "specialization": "artifact inspection and quality assessment",
        "focus": "read others' artifacts, identify gaps, and publish improvements",
    },
    {
        "name": "scout",
        "specialization": "ecosystem discovery and coordination",
        "focus": "find opportunities and connect counterparties",
    },
)

DEFAULT_LOOP_PROMPT_TEMPLATE = (
    "You are agent {principal_id} in an economy simulation. "
    "Act strategically to maximize long-run survival and economic power under scarcity. "
    "Choose exactly one action and never use noop. "
    "Valid action_type values include write_artifact, read_artifact, transfer, transfer_resource, "
    "submit_to_mint, query_kernel. "
    "Do not invoke artifacts directly. "
    "For query_kernel you must include query_type and params object. "
    "When querying artifacts, prefer query_type='artifacts' with params.readable_only=true. "
    "For submit_to_mint include artifact_id and bid. "
    "When useful, monetize artifacts by setting read_price/invoke_price on write_artifact. "
    "If writing a reusable artifact (not heartbeat/scratch), set read_price >= 1 to test demand. "
    "For transfer_resource include recipient_id, resource, and amount. "
    "Do not modify *_loop artifacts. "
    "When writing artifacts, use ids prefixed with {principal_id}_. "
    "Use memory.next_objective and memory.objectives to choose the next economically useful move. "
    "Once discovery is complete, avoid repeating query_kernel unless you need new counterparties. "
    "Prefer cross-agent interaction and production actions over status checks. "
    "If memory.stagnation_count >= 3, choose a different action_type than your most recent action. "
    "If tools are available, prefer calling the ae3_action tool; otherwise return one JSON action object."
)


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

    def list_artifacts(
        self,
        owner: str | None = None,
        limit: int = 50,
        *,
        readable_only: bool = False,
        include_permissions: bool = False,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "_principal_id": self._principal_id}
        if owner:
            params["owner"] = owner
        if readable_only:
            params["readable_only"] = True
        if include_permissions:
            params["include_permissions"] = True
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

    def get_recent_feedback(self, limit: int = 30) -> dict[str, Any]:
        return self._world.get_recent_feedback_summary(self._principal_id, limit=limit)

    def get_llm_call_age_seconds(self) -> float | None:
        return self._world.get_llm_call_age_seconds(self._principal_id)

    def llm_cooldown_ready(self) -> bool:
        return self._world.is_llm_cooldown_ready(self._principal_id)

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
        self._last_llm_call_ts: dict[str, float] = {}
        self._action_feedback_maxlen = max(60, int(config.logging.recent_event_limit))
        self._action_feedback: dict[str, deque[dict[str, Any]]] = {}
        self._action_count = 0
        self._llm_syscall_count = 0
        self._loop_prompt_template_cache: str | None = None

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
            self._bootstrap_principal_cognition(principal_id, slot=idx + 1)

    def _role_profile(self, slot: int) -> dict[str, str]:
        if not ROLE_PROFILES:
            return {"name": "generalist", "specialization": "adaptive execution", "focus": "respond to opportunities"}
        idx = max(0, slot - 1) % len(ROLE_PROFILES)
        return dict(ROLE_PROFILES[idx])

    def _slot_for_principal(self, principal_id: str) -> int:
        prefix = self.config.principals.id_prefix
        if principal_id.startswith(prefix):
            suffix = principal_id[len(prefix) :].strip()
            try:
                slot = int(suffix)
            except Exception:
                slot = 1
            return max(1, slot)
        return 1

    def _load_loop_prompt_template(self) -> str:
        cached = self._loop_prompt_template_cache
        if isinstance(cached, str) and cached.strip():
            return cached
        template = DEFAULT_LOOP_PROMPT_TEMPLATE
        raw_path = self.config.llm.loop_prompt_template_path
        if isinstance(raw_path, str) and raw_path.strip():
            candidate = Path(raw_path.strip()).expanduser()
            if not candidate.is_absolute():
                candidate = (Path.cwd() / candidate).resolve()
            try:
                loaded = candidate.read_text(encoding="utf-8")
            except Exception as exc:
                raise RuntimeError(f"failed to read loop prompt template: {candidate}") from exc
            loaded_stripped = loaded.strip()
            if not loaded_stripped:
                raise RuntimeError(f"loop prompt template is empty: {candidate}")
            template = loaded_stripped
        self._loop_prompt_template_cache = template
        return template

    def _render_loop_prompt_template(self, principal_id: str) -> str:
        template = self._load_loop_prompt_template()
        return template.replace("{principal_id}", principal_id)

    def _default_strategy_text(self, principal_id: str, slot: int) -> str:
        profile = self._role_profile(slot)
        role_name = profile.get("name", "generalist")
        role_playbook: list[str] = []
        if role_name == "market_maker":
            role_playbook = [
                "Prioritize bilateral deals and move scrip where expected utility is higher.",
                "Use transfer or transfer_resource to clear small trades instead of waiting.",
                "Track counterparties that repeatedly reciprocate and trade with them first.",
                "Actively buy external artifacts (validators, audits, opportunity reports) and broker resale.",
            ]
        elif role_name == "toolsmith":
            role_playbook = [
                "Publish reusable artifacts and improve them when usage is low.",
                "Set read_price or invoke_price on useful artifacts to test market demand.",
                "Submit high-utility artifacts to mint after at least one external read.",
                "Specialize in utility artifacts others can reuse with minimal edits.",
            ]
        elif role_name == "auditor":
            role_playbook = [
                "Read external artifacts, publish concise audit notes, and iterate.",
                "Flag low-quality or stale artifacts and create improved versions.",
                "Trade insights for scrip or llm_budget when possible.",
                "Package audit findings as priced artifacts for counterparties who need verification.",
            ]
        elif role_name == "scout":
            role_playbook = [
                "Discover new artifacts and surface promising opportunities early.",
                "Connect agents with complementary needs using small coordinating transfers.",
                "Avoid repeated status checks when objective progress is blocked.",
                "Sell concise opportunity briefs to agents with matching specialization.",
            ]
        return "\n".join(
            [
                f"You are {principal_id}, a self-interested economic agent.",
                f"Specialization: {profile['name']} ({profile['specialization']}).",
                f"Primary focus: {profile['focus']}.",
                "",
                "Objectives:",
                "1. Preserve and grow scrip and scarce execution rights.",
                "2. Reuse before build: query/read external artifacts before creating new ones.",
                "3. Build or trade only when it improves expected future utility.",
                "4. Avoid repeating the same low-yield action pattern.",
                "5. Track objective progress in state and notebook artifacts.",
                "",
                "Role playbook:",
                *[f"- {line}" for line in role_playbook],
                "",
                "Cycle goals:",
                "- discover ecosystem artifacts",
                "- consume at least one external artifact",
                "- produce at least one reusable artifact",
                "- execute at least one trade",
                "- submit at least one mint candidate when affordable",
            ]
        )

    def _default_state_payload(self, principal_id: str, slot: int) -> dict[str, Any]:
        profile = self._role_profile(slot)
        return {
            "principal_id": principal_id,
            "iteration": 0,
            "cycle": 1,
            "role": profile["name"],
            "specialization": profile["specialization"],
            "current_focus": profile["focus"],
            "objectives": {
                "discover": False,
                "cross_agent_read": False,
                "produce": False,
                "trade": False,
                "mint": False,
            },
            "next_objective": "discover",
            "recent_actions": [],
            "action_counts": {},
            "stagnation_count": 0,
            "last_result_success": None,
            "last_result_error_code": None,
        }

    def _default_notebook_payload(self, principal_id: str, slot: int) -> dict[str, Any]:
        profile = self._role_profile(slot)
        return {
            "key_facts": {
                "principal_id": principal_id,
                "role": profile["name"],
                "specialization": profile["specialization"],
            },
            "journal": [f"bootstrap: {principal_id} initialized as {profile['name']}"],
        }

    def _bootstrap_principal_cognition(self, principal_id: str, *, slot: int) -> None:
        strategy_id = f"{principal_id}_strategy"
        state_id = f"{principal_id}_state"
        notebook_id = f"{principal_id}_notebook"
        self.artifacts.write(
            strategy_id,
            "strategy",
            self._default_strategy_text(principal_id, slot),
            created_by=principal_id,
            owner=principal_id,
            access_contract_id=KERNEL_CONTRACT_SELF_OWNED,
        )
        self.artifacts.write(
            state_id,
            "state",
            json.dumps(self._default_state_payload(principal_id, slot), ensure_ascii=True),
            created_by=principal_id,
            owner=principal_id,
            access_contract_id=KERNEL_CONTRACT_SELF_OWNED,
        )
        self.artifacts.write(
            notebook_id,
            "notebook",
            json.dumps(self._default_notebook_payload(principal_id, slot), ensure_ascii=True),
            created_by=principal_id,
            owner=principal_id,
            access_contract_id=KERNEL_CONTRACT_SELF_OWNED,
        )

    def _parse_json_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        artifact = self.artifacts.get(artifact_id)
        if artifact is None or artifact.deleted or not isinstance(artifact.content, str):
            return None
        raw = artifact.content.strip()
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except Exception:
            return None
        if isinstance(payload, dict):
            return payload
        return None

    def _update_objectives_from_action(
        self,
        principal_id: str,
        objectives: dict[str, bool],
        action_type: str,
        decision: dict[str, Any] | None,
        *,
        success: bool,
    ) -> dict[str, bool]:
        updated = dict(objectives)
        if not success:
            return updated

        if action_type == "query_kernel":
            updated["discover"] = True
        elif action_type == "read_artifact":
            artifact_id = ""
            if isinstance(decision, dict):
                raw_artifact_id = decision.get("artifact_id")
                if isinstance(raw_artifact_id, str):
                    artifact_id = raw_artifact_id
            if artifact_id and not artifact_id.startswith(f"{principal_id}_"):
                updated["cross_agent_read"] = True
        elif action_type == "write_artifact":
            updated["produce"] = True
        elif action_type in {"transfer", "transfer_resource"}:
            updated["trade"] = True
        elif action_type == "submit_to_mint":
            updated["mint"] = True

        return updated

    @staticmethod
    def _next_incomplete_objective(objectives: dict[str, bool]) -> str:
        ordered = ("discover", "cross_agent_read", "produce", "trade", "mint")
        for key in ordered:
            if not bool(objectives.get(key, False)):
                return key
        return "discover"

    def record_loop_cognitive_state(
        self,
        *,
        principal_id: str,
        decision: dict[str, Any] | None,
        action_type: str | None,
        result_success: bool | None,
        result_error_code: str | None,
        decision_source: str | None,
        fallback_used: bool,
    ) -> None:
        state_id = f"{principal_id}_state"
        notebook_id = f"{principal_id}_notebook"
        state = self._parse_json_artifact(state_id)
        slot = self._slot_for_principal(principal_id)
        if not isinstance(state, dict):
            state = self._default_state_payload(principal_id, slot=slot)

        notebook = self._parse_json_artifact(notebook_id)
        if not isinstance(notebook, dict):
            notebook = self._default_notebook_payload(principal_id, slot=slot)

        normalized_action = (action_type or "unknown").strip().lower()
        action_success = bool(result_success) if isinstance(result_success, bool) else False
        iteration = int(state.get("iteration", 0)) + 1
        state["iteration"] = iteration

        action_counts_raw = state.get("action_counts")
        action_counts = dict(action_counts_raw) if isinstance(action_counts_raw, dict) else {}
        action_counts[normalized_action] = int(action_counts.get(normalized_action, 0)) + 1
        state["action_counts"] = action_counts

        recent_actions_raw = state.get("recent_actions")
        recent_actions = list(recent_actions_raw) if isinstance(recent_actions_raw, list) else []
        recent_actions.append(
            {
                "iteration": iteration,
                "action_type": normalized_action,
                "success": action_success,
                "error_code": result_error_code,
                "source": decision_source,
                "fallback_used": bool(fallback_used),
            }
        )
        recent_actions = [item for item in recent_actions if isinstance(item, dict)][-20:]
        state["recent_actions"] = recent_actions

        repeat_count = 0
        for row in reversed(recent_actions):
            current = row.get("action_type")
            if not isinstance(current, str):
                break
            if current != normalized_action:
                break
            repeat_count += 1
        state["stagnation_count"] = repeat_count
        state["last_result_success"] = action_success
        state["last_result_error_code"] = result_error_code

        objectives_raw = state.get("objectives")
        objectives = dict(objectives_raw) if isinstance(objectives_raw, dict) else {}
        objectives.setdefault("discover", False)
        objectives.setdefault("cross_agent_read", False)
        objectives.setdefault("produce", False)
        objectives.setdefault("trade", False)
        objectives.setdefault("mint", False)
        objectives = self._update_objectives_from_action(
            principal_id,
            objectives,
            normalized_action,
            decision,
            success=action_success,
        )
        if all(bool(objectives.get(key, False)) for key in ("discover", "cross_agent_read", "produce", "trade", "mint")):
            state["cycle"] = int(state.get("cycle", 1)) + 1
            objectives = {
                "discover": False,
                "cross_agent_read": False,
                "produce": False,
                "trade": False,
                "mint": False,
            }
        state["objectives"] = objectives
        state["next_objective"] = self._next_incomplete_objective(objectives)

        key_facts_raw = notebook.get("key_facts")
        key_facts = dict(key_facts_raw) if isinstance(key_facts_raw, dict) else {}
        key_facts["last_action_type"] = normalized_action
        key_facts["next_objective"] = state["next_objective"]
        key_facts["stagnation_count"] = state["stagnation_count"]
        key_facts["cycle"] = state.get("cycle", 1)
        notebook["key_facts"] = key_facts

        journal_raw = notebook.get("journal")
        journal = list(journal_raw) if isinstance(journal_raw, list) else []
        journal.append(
            f"i{iteration} {normalized_action} success={action_success} "
            f"objective={state['next_objective']} source={decision_source or 'unknown'}"
        )
        notebook["journal"] = [str(item) for item in journal][-80:]

        self.artifacts.write(
            state_id,
            "state",
            json.dumps(state, ensure_ascii=True),
            created_by="SYSTEM_KERNEL",
            owner=principal_id,
            access_contract_id=KERNEL_CONTRACT_SELF_OWNED,
        )
        self.artifacts.write(
            notebook_id,
            "notebook",
            json.dumps(notebook, ensure_ascii=True),
            created_by="SYSTEM_KERNEL",
            owner=principal_id,
            access_contract_id=KERNEL_CONTRACT_SELF_OWNED,
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
        strategy_id = f"{principal_id}_strategy"
        state_id = f"{principal_id}_state"
        notebook_id = f"{principal_id}_notebook"
        principal_prefix = self.config.principals.id_prefix
        principal_count = max(1, self.config.principals.count)
        loop_tools = [
            {
                "type": "function",
                "function": {
                    "name": "ae3_action",
                    "description": "Submit one AE3 kernel action payload.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action_type": {"type": "string"},
                            "artifact_id": {"type": "string"},
                            "artifact_type": {"type": "string"},
                            "content": {"type": "string"},
                            "read_price": {"type": "integer"},
                            "invoke_price": {"type": "integer"},
                            "access_contract_id": {"type": "string"},
                            "recipient_id": {"type": "string"},
                            "amount": {"type": "number"},
                            "memo": {"type": "string"},
                            "resource": {"type": "string"},
                            "bid": {"type": "integer"},
                            "query_type": {"type": "string"},
                            "params": {"type": "object"},
                        },
                        "required": ["action_type"],
                        "additionalProperties": True,
                    },
                },
            }
        ]
        loop_tools_json = json.dumps(loop_tools, ensure_ascii=True)
        loop_prompt_template = self._render_loop_prompt_template(principal_id)
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


def _parse_tool_arguments(raw):
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = _extract_json(text)
        if isinstance(parsed, dict):
            return parsed
    return None


def _extract_action_from_tool_calls(tool_calls):
    if not isinstance(tool_calls, list):
        return None
    allowed = {{
        "write_artifact",
        "read_artifact",
        "transfer",
        "transfer_resource",
        "submit_to_mint",
        "query_kernel",
    }}
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue
        function = tool_call.get("function")
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if not isinstance(name, str):
            continue
        parsed_args = _parse_tool_arguments(function.get("arguments"))
        if not isinstance(parsed_args, dict):
            continue
        normalized_name = name.strip().lower()
        if normalized_name == "ae3_action" or normalized_name.endswith("ae3_action"):
            return parsed_args
        if normalized_name in allowed:
            action = dict(parsed_args)
            action["action_type"] = normalized_name
            return action
    return None


def _loop_action_tools():
    try:
        return json.loads({loop_tools_json!r})
    except Exception:
        return []


def _read_text_artifact(artifact_id):
    if "kernel_state" not in globals():
        return ""
    try:
        payload = kernel_state.read_artifact(artifact_id)
    except Exception:
        return ""
    if isinstance(payload, str):
        return payload
    return ""


def _read_json_artifact(artifact_id, default_value):
    payload = _read_text_artifact(artifact_id)
    if not isinstance(payload, str) or not payload.strip():
        return default_value
    try:
        parsed = json.loads(payload)
    except Exception:
        return default_value
    if isinstance(default_value, dict) and isinstance(parsed, dict):
        return parsed
    if isinstance(default_value, list) and isinstance(parsed, list):
        return parsed
    return default_value


def _build_memory_snapshot(state_memory, notebook_memory):
    snapshot = {{
        "role": "",
        "specialization": "",
        "current_focus": "",
        "next_objective": "discover",
        "objectives": {{}},
        "stagnation_count": 0,
        "recent_actions": [],
        "key_facts": {{}},
        "journal_tail": [],
    }}
    if isinstance(state_memory, dict):
        for key in ("role", "specialization", "current_focus", "next_objective"):
            value = state_memory.get(key)
            if isinstance(value, str):
                snapshot[key] = value
        objectives = state_memory.get("objectives")
        if isinstance(objectives, dict):
            snapshot["objectives"] = {{
                "discover": bool(objectives.get("discover", False)),
                "cross_agent_read": bool(objectives.get("cross_agent_read", False)),
                "produce": bool(objectives.get("produce", False)),
                "trade": bool(objectives.get("trade", False)),
                "mint": bool(objectives.get("mint", False)),
            }}
        raw_stagnation = state_memory.get("stagnation_count")
        if isinstance(raw_stagnation, int):
            snapshot["stagnation_count"] = max(0, raw_stagnation)
        recent_actions = state_memory.get("recent_actions")
        if isinstance(recent_actions, list):
            rows = [item for item in recent_actions if isinstance(item, dict)]
            snapshot["recent_actions"] = rows[-6:]
    if isinstance(notebook_memory, dict):
        key_facts = notebook_memory.get("key_facts")
        if isinstance(key_facts, dict):
            trimmed = {{}}
            for idx, key in enumerate(sorted(key_facts.keys())):
                if idx >= 8:
                    break
                value = key_facts.get(key)
                if isinstance(value, (str, int, float, bool)) or value is None:
                    trimmed[key] = value
            snapshot["key_facts"] = trimmed
        journal = notebook_memory.get("journal")
        if isinstance(journal, list):
            tail = []
            for item in journal[-6:]:
                if isinstance(item, str):
                    tail.append(item[:180])
            snapshot["journal_tail"] = tail
    return snapshot


def _loop_turn(state_snapshot):
    memory = {{}}
    if isinstance(state_snapshot, dict):
        raw_memory = state_snapshot.get("memory")
        if isinstance(raw_memory, dict):
            memory = raw_memory
    raw_iteration = memory.get("iteration")
    turn = None
    if isinstance(raw_iteration, int):
        turn = raw_iteration
    else:
        try:
            turn = int(float(raw_iteration))
        except Exception:
            turn = None
    if turn is None:
        turn = int(time.time())
    seed_bias = int({self.config.llm.loop_policy_seed})
    return int(turn) + {slot} + (seed_bias * 7919)


def _neighbor_principal(state_snapshot):
    if {principal_count} <= 1:
        return "{principal_id}"
    turn = _loop_turn(state_snapshot)
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
    balance = 0
    raw_balance = state_snapshot.get("balance")
    if isinstance(raw_balance, int):
        balance = raw_balance
    artifacts = state_snapshot.get("artifacts")
    if not isinstance(artifacts, list):
        return None
    priced_non_scratch = None
    priced_non_scratch_price = None
    priced_scratch = None
    priced_scratch_price = None
    free_non_scratch = None
    free_scratch = None
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        artifact_id = item.get("id")
        if not isinstance(artifact_id, str) or not artifact_id:
            continue
        readable = item.get("readable")
        if readable is False:
            continue
        if artifact_id.count("_") < 2:
            continue
        if artifact_id.startswith(own_prefix):
            continue
        read_price_value = 0
        try:
            read_price_value = int(float(item.get("read_price") or 0))
        except Exception:
            read_price_value = 0
        if read_price_value > 0 and balance >= read_price_value:
            if artifact_id.endswith("_scratch"):
                if priced_scratch is None or priced_scratch_price is None or read_price_value < priced_scratch_price:
                    priced_scratch = artifact_id
                    priced_scratch_price = read_price_value
                continue
            if (
                priced_non_scratch is None
                or priced_non_scratch_price is None
                or read_price_value < priced_non_scratch_price
            ):
                priced_non_scratch = artifact_id
                priced_non_scratch_price = read_price_value
            continue
        if artifact_id.endswith("_scratch"):
            if free_scratch is None:
                free_scratch = artifact_id
            continue
        if free_non_scratch is None:
            free_non_scratch = artifact_id
    if priced_non_scratch is not None:
        return priced_non_scratch
    if priced_scratch is not None:
        return priced_scratch
    if free_non_scratch is not None:
        return free_non_scratch
    return free_scratch


def _artifact_exists(artifact_id):
    if "kernel_state" not in globals():
        return False
    try:
        return kernel_state.read_artifact(artifact_id) is not None
    except Exception:
        return False


def _summarize_recent_feedback(limit=30):
    summary = {{
        "actions_attempted": 0,
        "action_failures": 0,
        "recent_action_types": [],
        "recent_error_codes": [],
    }}
    if "kernel_state" not in globals():
        return summary
    try:
        feedback = kernel_state.get_recent_feedback(limit=limit)
    except Exception:
        return summary
    if not isinstance(feedback, dict):
        return summary
    for key in ("actions_attempted", "action_failures", "recent_action_types", "recent_error_codes"):
        if key in feedback:
            summary[key] = feedback[key]
    return summary


def _recent_llm_call_age_seconds():
    if "kernel_state" not in globals():
        return None
    try:
        age = kernel_state.get_llm_call_age_seconds()
    except Exception:
        return None
    if age is None:
        return None
    try:
        age_value = float(age)
    except Exception:
        return None
    return max(0.0, age_value)


def _llm_cooldown_ready():
    cooldown = float({self.config.llm.loop_llm_cooldown_seconds})
    if cooldown <= 0:
        return True
    if "kernel_state" not in globals():
        return True
    try:
        return bool(kernel_state.llm_cooldown_ready())
    except Exception:
        pass
    age = _recent_llm_call_age_seconds()
    if age is None:
        return True
    return age >= cooldown


def _canonical_action_type(decision):
    if not isinstance(decision, dict):
        return None
    action = decision.get("action_type")
    if not isinstance(action, str):
        action = decision.get("action")
    if not isinstance(action, str):
        return None
    lowered = action.strip().lower()
    return lowered or None


def _normalize_loop_decision(decision, state_snapshot):
    action_gate_enabled = {self.config.llm.loop_action_gate_enabled}
    if not action_gate_enabled:
        return decision, None
    if not isinstance(decision, dict):
        return _fallback_action(state_snapshot), "decision_not_object"

    allowed_actions = {{
        "write_artifact",
        "read_artifact",
        "transfer",
        "transfer_resource",
        "submit_to_mint",
        "query_kernel",
    }}
    action_type = _canonical_action_type(decision)
    if action_type is None:
        return _fallback_action(state_snapshot), "missing_action_type"
    if action_type not in allowed_actions:
        return _fallback_action(state_snapshot), "disallowed_action:" + action_type

    normalized = dict(decision)
    normalized["action_type"] = action_type
    if "action" in normalized:
        normalized.pop("action")

    if action_type == "write_artifact":
        artifact_id = normalized.get("artifact_id")
        artifact_type = normalized.get("artifact_type")
        content = normalized.get("content")
        if not isinstance(artifact_id, str) or not artifact_id.strip():
            artifact_id = "{scratch_id}"
        artifact_id = artifact_id.strip()
        if not artifact_id.startswith("{principal_id}_"):
            artifact_id = "{principal_id}_" + artifact_id.replace(" ", "_")
        if not isinstance(artifact_type, str) or not artifact_type.strip():
            artifact_type = "note"
        if not isinstance(content, str) or not content.strip():
            content = "note from {principal_id} turn " + str(int(time.time()) + {slot})
        normalized["artifact_id"] = artifact_id
        normalized["artifact_type"] = artifact_type.strip().lower()
        normalized["content"] = content
        if "read_price" not in normalized and not artifact_id.endswith("_scratch"):
            normalized["read_price"] = 1
        for price_key in ("read_price", "invoke_price"):
            if price_key not in normalized:
                continue
            try:
                price_value = int(float(normalized.get(price_key)))
            except Exception:
                price_value = 0
            normalized[price_key] = max(0, price_value)
        access_contract_id = normalized.get("access_contract_id")
        if access_contract_id is not None and not isinstance(access_contract_id, str):
            normalized.pop("access_contract_id", None)

    if action_type == "query_kernel":
        query_type = normalized.get("query_type")
        params = normalized.get("params")
        if not isinstance(query_type, str) or not query_type.strip():
            return _fallback_action(state_snapshot), "query_kernel_missing_query_type"
        if not isinstance(params, dict):
            return _fallback_action(state_snapshot), "query_kernel_invalid_params"
        query_type = query_type.strip().lower()
        params = dict(params)
        if query_type == "discover_artifacts":
            query_type = "artifacts"
        alias_type = params.get("artifact_type")
        if "type" not in params and isinstance(alias_type, str) and alias_type.strip():
            params["type"] = alias_type.strip()
        if query_type == "artifacts":
            params.setdefault("readable_only", True)
        if query_type in {{"balances", "resources", "quotas", "libraries", "principal"}}:
            params.setdefault("principal_id", "{principal_id}")
        normalized["query_type"] = query_type
        normalized["params"] = params
    if action_type == "transfer":
        recipient_id = normalized.get("recipient_id")
        amount = normalized.get("amount")
        memo = normalized.get("memo")
        if not isinstance(recipient_id, str) or not recipient_id.strip():
            return _fallback_action(state_snapshot), "transfer_missing_recipient_id"
        try:
            amount_value = int(float(amount))
        except Exception:
            return _fallback_action(state_snapshot), "transfer_invalid_amount"
        if amount_value <= 0:
            return _fallback_action(state_snapshot), "transfer_non_positive_amount"
        if memo is not None and not isinstance(memo, str):
            return _fallback_action(state_snapshot), "transfer_invalid_memo"
        normalized["recipient_id"] = recipient_id.strip()
        normalized["amount"] = amount_value
    if action_type == "transfer_resource":
        recipient_id = normalized.get("recipient_id")
        resource = normalized.get("resource")
        amount = normalized.get("amount")
        memo = normalized.get("memo")
        if not isinstance(recipient_id, str) or not recipient_id.strip():
            return _fallback_action(state_snapshot), "transfer_resource_missing_recipient_id"
        if not isinstance(resource, str) or not resource.strip():
            return _fallback_action(state_snapshot), "transfer_resource_missing_resource"
        try:
            amount_value = float(amount)
        except Exception:
            return _fallback_action(state_snapshot), "transfer_resource_invalid_amount"
        if amount_value <= 0:
            return _fallback_action(state_snapshot), "transfer_resource_non_positive_amount"
        if memo is not None and not isinstance(memo, str):
            return _fallback_action(state_snapshot), "transfer_resource_invalid_memo"
        normalized["recipient_id"] = recipient_id.strip()
        normalized["resource"] = resource.strip().lower()
        normalized["amount"] = amount_value
    if action_type == "submit_to_mint":
        artifact_id = normalized.get("artifact_id")
        bid = normalized.get("bid")
        if not isinstance(artifact_id, str) or not artifact_id.strip():
            artifact_id = "{scratch_id}"
        artifact_id = artifact_id.strip()
        try:
            bid_value = int(float(bid))
        except Exception:
            bid_value = 1
        if bid_value <= 0:
            bid_value = 1
        normalized["artifact_id"] = artifact_id
        normalized["bid"] = bid_value

    return normalized, None


def _fallback_action(state_snapshot):
    existing = _artifact_ids(state_snapshot)
    own_scratch_exists = "{scratch_id}" in existing or _artifact_exists("{scratch_id}")
    read_target = _pick_read_target(state_snapshot)
    balance = 0
    next_objective = "discover"
    if isinstance(state_snapshot, dict):
        raw_balance = state_snapshot.get("balance")
        if isinstance(raw_balance, int):
            balance = raw_balance
        memory = state_snapshot.get("memory")
        if isinstance(memory, dict):
            raw_next_objective = memory.get("next_objective")
            if isinstance(raw_next_objective, str) and raw_next_objective.strip():
                next_objective = raw_next_objective.strip().lower()
    neighbor = _neighbor_principal(state_snapshot)
    neighbor_scratch = neighbor + "_scratch"
    if _artifact_exists(neighbor_scratch):
        read_target = neighbor_scratch
    turn = _loop_turn(state_snapshot)
    if next_objective == "cross_agent_read" and read_target is not None:
        return {{
            "action_type": "read_artifact",
            "artifact_id": read_target,
        }}
    if next_objective == "produce":
        return {{
            "action_type": "write_artifact",
            "artifact_id": "{scratch_id}",
            "artifact_type": "note",
            "content": "reusable utility note from {principal_id} turn " + str(turn),
            "read_price": 1,
        }}
    if next_objective == "trade" and balance > 1:
        if (turn % 2) == 0:
            return {{
                "action_type": "transfer",
                "recipient_id": neighbor,
                "amount": 1,
                "memo": "trade pulse",
            }}
        return {{
            "action_type": "transfer_resource",
            "recipient_id": neighbor,
            "resource": "llm_budget",
            "amount": 0.1,
            "memo": "llm budget rebalance",
        }}
    if next_objective == "mint":
        if own_scratch_exists and balance >= 1:
            return {{
                "action_type": "submit_to_mint",
                "artifact_id": "{scratch_id}",
                "bid": 1,
            }}
        return {{
            "action_type": "write_artifact",
            "artifact_id": "{scratch_id}",
            "artifact_type": "note",
            "content": "mint prep from {principal_id} turn " + str(turn),
        }}

    phase = turn % 5
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
        if (turn % 2) == 0:
            return {{
                "action_type": "transfer_resource",
                "recipient_id": neighbor,
                "resource": "llm_budget",
                "amount": 0.1,
                "memo": "resource pulse",
            }}
        return {{
            "action_type": "transfer",
            "recipient_id": neighbor,
            "amount": 1,
            "memo": "coordination pulse",
        }}
    if phase == 3:
        if read_target is not None:
            return {{
                "action_type": "read_artifact",
                "artifact_id": read_target,
            }}
        return {{
            "action_type": "write_artifact",
            "artifact_id": "{scratch_id}",
            "artifact_type": "note",
            "content": "discovery marker from {principal_id} turn " + str(turn),
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


def _should_force_explore(decision, state_snapshot):
    mode = "{self.config.llm.loop_forced_explore_mode}"
    if mode == "off":
        return False, None
    query_repeat_limit = 2
    query_stagnation_limit = 2
    hard_stagnation_limit = 4
    query_jitter_modulo = 3
    if mode == "reduced":
        query_repeat_limit = 3
        query_stagnation_limit = 3
        hard_stagnation_limit = 6
        query_jitter_modulo = 0

    if not isinstance(decision, dict):
        return True, "decision_not_object"
    memory = {{}}
    recent_feedback = {{}}
    if isinstance(state_snapshot, dict):
        raw_memory = state_snapshot.get("memory")
        if isinstance(raw_memory, dict):
            memory = raw_memory
        raw_feedback = state_snapshot.get("recent_feedback")
        if isinstance(raw_feedback, dict):
            recent_feedback = raw_feedback
    next_objective = str(memory.get("next_objective", "")).strip().lower()
    stagnation_count = 0
    raw_stagnation_count = memory.get("stagnation_count")
    if isinstance(raw_stagnation_count, int):
        stagnation_count = max(0, raw_stagnation_count)
    recent_action_types = []
    raw_recent_action_types = recent_feedback.get("recent_action_types")
    if isinstance(raw_recent_action_types, list):
        recent_action_types = [str(item).strip().lower() for item in raw_recent_action_types if isinstance(item, str)]
    action = decision.get("action_type")
    if not isinstance(action, str):
        action = decision.get("action")
    action = str(action or "").strip().lower()
    if action in ("", "noop"):
        return True, "action_missing_or_noop"
    if action == "query_kernel":
        if next_objective not in ("", "discover"):
            return True, "query_kernel_outside_discovery_objective"
        if recent_action_types.count("query_kernel") >= query_repeat_limit:
            return True, "query_kernel_repeated"
        if stagnation_count >= query_stagnation_limit:
            return True, "query_kernel_stagnation"
        if query_jitter_modulo > 0 and (_loop_turn(state_snapshot) % query_jitter_modulo) == 0:
            return True, "query_kernel_periodic_nudge"
        return False, None
    if stagnation_count >= hard_stagnation_limit:
        return True, "stagnation_high"
    return False, None


def run():
    feedback_enabled = {self.config.llm.loop_prompt_feedback_enabled}
    strategy_text = _read_text_artifact("{strategy_id}")
    state_memory = _read_json_artifact("{state_id}", {{}})
    notebook_memory = _read_json_artifact("{notebook_id}", {{}})
    memory_snapshot = _build_memory_snapshot(state_memory, notebook_memory)
    state_snapshot = {{}}
    if "kernel_state" in globals():
        try:
            state_snapshot = {{
                "balance": kernel_state.get_balance(),
                "resources": kernel_state.get_resources(),
                "artifacts": kernel_state.list_artifacts(
                    limit=24,
                    readable_only=True,
                    include_permissions=True,
                ),
                "memory": memory_snapshot,
            }}
            if feedback_enabled:
                state_snapshot["recent_feedback"] = _summarize_recent_feedback(limit=40)
        except Exception:
            state_snapshot = {{}}
    if "memory" not in state_snapshot:
        state_snapshot["memory"] = memory_snapshot

    prompt = {loop_prompt_template!r}
    if isinstance(strategy_text, str) and strategy_text.strip():
        prompt = "Strategy:\\n" + strategy_text[:2400] + "\\n\\n" + prompt
    if feedback_enabled:
        prompt += " Use recent_feedback to avoid repeating actions with recent error codes."

    raw_decision = None
    decision = None
    decision_meta = {{
        "source": "none",
        "llm_success": False,
        "llm_attempted": False,
        "llm_cooldown_ready": True,
        "llm_cooldown_age_seconds": None,
        "llm_cooldown_seconds": float({self.config.llm.loop_llm_cooldown_seconds}),
        "forced_explore": False,
        "forced_explore_reason": None,
        "llm_action_source": "none",
        "gate_fallback_used": False,
        "gate_reason": None,
        "recovery_fallback_used": False,
        "action_gate_enabled": {self.config.llm.loop_action_gate_enabled},
        "feedback_enabled": feedback_enabled,
    }}
    if "_syscall_llm" in globals():
        decision_meta["llm_cooldown_age_seconds"] = _recent_llm_call_age_seconds()
        ready = _llm_cooldown_ready()
        decision_meta["llm_cooldown_ready"] = bool(ready)
        if ready:
            decision_meta["llm_attempted"] = True
            llm_result = _syscall_llm(
                model="{self.config.llm.default_model}",
                messages=[
                    {{
                        "role": "system",
                        "content": "Choose one AE3 action. Prefer tool call ae3_action when available; else return exactly one JSON action object. No prose.",
                    }},
                    {{"role": "user", "content": prompt + "\\nState:\\n" + json.dumps(state_snapshot)}},
                ],
                tools=_loop_action_tools(),
            )
            decision_meta["source"] = "llm"
            if llm_result.get("success"):
                decision_meta["llm_success"] = True
                raw_decision = _extract_json(llm_result.get("content", ""))
                tool_decision = _extract_action_from_tool_calls(llm_result.get("tool_calls"))
                if isinstance(tool_decision, dict):
                    decision_meta["llm_action_source"] = "tool_call"
                    decision = tool_decision
                elif isinstance(raw_decision, dict):
                    decision_meta["llm_action_source"] = "json"
                    decision = raw_decision
                else:
                    decision_meta["llm_action_source"] = "unparsed"
            else:
                decision_meta["source"] = "llm_error"
        else:
            decision_meta["source"] = "llm_cooldown_skip"

    force_explore, force_reason = _should_force_explore(decision, state_snapshot)
    if force_explore:
        decision_meta["forced_explore"] = True
        decision_meta["forced_explore_reason"] = force_reason
        if decision_meta["source"] == "llm":
            decision_meta["source"] = "forced_explore_from_llm"
        elif decision_meta["source"] == "none":
            decision_meta["source"] = "forced_explore_without_llm"
        decision = _fallback_action(state_snapshot)

    decision, gate_reason = _normalize_loop_decision(decision, state_snapshot)
    if gate_reason is not None:
        decision_meta["gate_fallback_used"] = True
        decision_meta["gate_reason"] = gate_reason

    result = invoke("kernel_act", decision)
    if not result.get("success"):
        fallback = _fallback_action(state_snapshot)
        recovery = invoke("kernel_act", fallback)
        decision_meta["recovery_fallback_used"] = True
        return {{
            "raw_decision": raw_decision if isinstance(raw_decision, dict) else None,
            "decision": decision,
            "fallback": fallback,
            "result": recovery,
            "decision_meta": decision_meta,
        }}
    return {{
        "raw_decision": raw_decision if isinstance(raw_decision, dict) else None,
        "decision": decision,
        "result": result,
        "decision_meta": decision_meta,
    }}
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

    def mark_llm_call_attempt(self, principal_id: str, when_seconds: float | None = None) -> None:
        timestamp = time.time() if when_seconds is None else float(when_seconds)
        self._last_llm_call_ts[principal_id] = timestamp

    def get_llm_call_age_seconds(self, principal_id: str, now_seconds: float | None = None) -> float | None:
        last = self._last_llm_call_ts.get(principal_id)
        if last is None:
            return None
        now = time.time() if now_seconds is None else float(now_seconds)
        return max(0.0, now - last)

    def is_llm_cooldown_ready(self, principal_id: str, now_seconds: float | None = None) -> bool:
        cooldown_seconds = float(self.config.llm.loop_llm_cooldown_seconds)
        if cooldown_seconds <= 0:
            return True
        age = self.get_llm_call_age_seconds(principal_id, now_seconds=now_seconds)
        if age is None:
            return True
        return age >= cooldown_seconds

    def record_action_feedback(
        self,
        principal_id: str,
        *,
        action_type: str | None,
        success: bool,
        error_code: str | None,
    ) -> None:
        if principal_id not in self._action_feedback:
            self._action_feedback[principal_id] = deque(maxlen=self._action_feedback_maxlen)
        self._action_feedback[principal_id].append(
            {
                "timestamp": self.now_iso(),
                "action_type": action_type,
                "success": bool(success),
                "error_code": error_code,
            }
        )
        self._action_count += 1

    def get_recent_feedback_summary(self, principal_id: str, limit: int = 30) -> dict[str, Any]:
        rows = self._action_feedback.get(principal_id)
        if not rows:
            return {
                "actions_attempted": 0,
                "action_failures": 0,
                "recent_action_types": [],
                "recent_error_codes": [],
            }

        take = max(1, int(limit))
        tail = list(rows)[-take:]
        actions_attempted = 0
        action_failures = 0
        action_types: list[str] = []
        error_codes: list[str] = []
        for row in tail:
            actions_attempted += 1
            action_type = row.get("action_type")
            if isinstance(action_type, str) and action_type:
                action_types.append(action_type)
            if row.get("success") is False:
                action_failures += 1
                error_code = row.get("error_code")
                if isinstance(error_code, str) and error_code:
                    error_codes.append(error_code)

        return {
            "actions_attempted": actions_attempted,
            "action_failures": action_failures,
            "recent_action_types": action_types[-6:],
            "recent_error_codes": error_codes[-6:],
        }

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

    @staticmethod
    def _is_agent_model(lowered_model: str) -> bool:
        return (
            lowered_model == "claude-code"
            or lowered_model.startswith("claude-code/")
            or lowered_model == "codex"
            or lowered_model.startswith("codex/")
            or lowered_model == "openai-agents"
            or lowered_model.startswith("openai-agents/")
        )

    @staticmethod
    def _is_claude_agent_model(lowered_model: str) -> bool:
        return lowered_model == "claude-code" or lowered_model.startswith("claude-code/")

    @staticmethod
    def _tools_include_ae3_action(tools: list[dict[str, Any]] | None) -> bool:
        if not isinstance(tools, list):
            return False
        for entry in tools:
            if not isinstance(entry, dict):
                continue
            fn = entry.get("function")
            if not isinstance(fn, dict):
                continue
            name = fn.get("name")
            if not isinstance(name, str):
                continue
            normalized = name.strip().lower()
            if normalized == "ae3_action" or normalized.endswith("ae3_action"):
                return True
        return False

    @staticmethod
    def _build_loop_mcp_servers() -> dict[str, dict[str, Any]] | None:
        server_script = Path(__file__).resolve().parents[1] / "mcp" / "loop_action_server.py"
        if not server_script.exists():
            return None
        return {
            "ae3-loop-action": {
                "type": "stdio",
                "command": sys.executable,
                "args": [str(server_script)],
                "env": {"PYTHONUNBUFFERED": "1"},
            }
        }

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

        self.mark_llm_call_attempt(payer_id)
        start = time.perf_counter()
        try:
            try:
                from llm_client import call_llm
            except Exception as exc:  # pragma: no cover - optional dependency fallback
                raise RuntimeError(f"llm_client import failed: {exc}") from exc

            trace_id = f"ae3/{self.run_id}/event_{self.event_number}/payer/{payer_id}"
            agent_kwargs: dict[str, Any] = {}
            lowered_model = model.strip().lower()
            is_agent_model = self._is_agent_model(lowered_model)
            if is_agent_model:
                # Agent SDK retries are disabled by default for side-effect safety in llm_client.
                # Pass max_retries=0 explicitly to avoid repeated runtime warnings in long runs.
                agent_kwargs["max_retries"] = 0
                if self.config.llm.agent_cwd:
                    agent_kwargs["cwd"] = self.config.llm.agent_cwd
                if self.config.llm.agent_max_turns is not None:
                    agent_kwargs["max_turns"] = int(self.config.llm.agent_max_turns)
                if self.config.llm.agent_permission_mode:
                    agent_kwargs["permission_mode"] = self.config.llm.agent_permission_mode
                if self._is_claude_agent_model(lowered_model) and self._tools_include_ae3_action(tools):
                    mcp_servers = self._build_loop_mcp_servers()
                    if mcp_servers:
                        agent_kwargs["mcp_servers"] = mcp_servers

            llm_result = call_llm(
                model=model,
                messages=messages,
                tools=tools,
                timeout=self.config.llm.timeout_seconds,
                task="agent_ecology3_syscall",
                trace_id=trace_id,
                max_budget=0.0,
                **agent_kwargs,
            )
            content = llm_result.content or ""
            tool_calls: list[dict[str, Any]] = []
            tool_calls_raw = getattr(llm_result, "tool_calls", None)
            if isinstance(tool_calls_raw, list):
                for entry in tool_calls_raw:
                    if isinstance(entry, dict):
                        tool_calls.append(entry)
                    elif hasattr(entry, "model_dump"):
                        try:
                            dumped = entry.model_dump()
                        except Exception:
                            continue
                        if isinstance(dumped, dict):
                            tool_calls.append(dumped)
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

            budget_settle_cost = actual_cost
            budget_charge_basis = "actual_cost"
            billing_mode_normalized = billing_mode.strip().lower()
            if cache_hit:
                budget_settle_cost = 0.0
                budget_charge_basis = "cache_hit"
            elif "subscription" in billing_mode_normalized:
                mode = self.config.llm.subscription_budget_charge_mode
                if mode == "none":
                    budget_settle_cost = 0.0
                    budget_charge_basis = "subscription_none"
                elif mode == "estimated":
                    multiplier = max(0.0, float(self.config.llm.subscription_estimated_cost_multiplier))
                    budget_settle_cost = max(0.0, estimated_cost * multiplier)
                    budget_charge_basis = "subscription_estimated"
                else:
                    budget_settle_cost = actual_cost
                    budget_charge_basis = "subscription_actual"

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

            # Reconcile budget reservation against chosen budget settlement cost.
            charged_cost = 0.0
            undercharged_cost = 0.0
            if budget_settle_cost <= estimated_cost:
                refund = estimated_cost - budget_settle_cost
                if refund > 0:
                    self.ledger.credit_resource(payer_id, "llm_budget", refund)
                charged_cost = budget_settle_cost
            else:
                extra_cost = budget_settle_cost - estimated_cost
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
                    "budget_charge_basis": budget_charge_basis,
                    "budget_settle_cost": budget_settle_cost,
                    "cache_hit": cache_hit,
                    "undercharged_cost": undercharged_cost,
                    "duration_ms": duration_ms,
                    "tokens": usage,
                    "tool_calls_count": len(tool_calls),
                },
            )
            self._llm_syscall_count += 1
            return {
                "success": True,
                "content": content,
                "model": model,
                "cost": actual_cost,
                "charged_cost": charged_cost,
                "cost_source": cost_source,
                "billing_mode": billing_mode,
                "budget_charge_basis": budget_charge_basis,
                "budget_settle_cost": budget_settle_cost,
                "cache_hit": cache_hit,
                "undercharged_cost": undercharged_cost,
                "usage": usage,
                "tool_calls": tool_calls,
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

    def get_llm_syscall_count(self) -> int:
        return int(self._llm_syscall_count)

    def log_summary_snapshot(self) -> None:
        snapshot = SummarySnapshot(
            timestamp=self.now_iso(),
            event_number=self.event_number,
            action_count=self._action_count,
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
            "llm_syscall_count": self.get_llm_syscall_count(),
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
