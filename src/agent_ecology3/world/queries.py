"""Kernel query handling for `query_kernel` action."""

from __future__ import annotations

from typing import Any


class KernelQueryHandler:
    def __init__(self, world: Any) -> None:
        self.world = world

    def execute(self, query_type: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        handler = getattr(self, f"_query_{query_type}", None)
        if handler is None:
            return {
                "success": False,
                "error": f"unknown query_type '{query_type}'",
                "error_code": "invalid_query_type",
            }
        return handler(params)

    def _query_artifacts(self, params: dict[str, Any]) -> dict[str, Any]:
        owner = params.get("owner")
        artifact_type = params.get("type")
        executable = params.get("executable")
        limit = int(params.get("limit", 50))
        offset = int(params.get("offset", 0))

        items = []
        for artifact in self.world.artifacts.artifacts.values():
            if artifact.deleted:
                continue
            if owner and artifact.owner != owner:
                continue
            if artifact_type and artifact.type != artifact_type:
                continue
            if executable is not None and artifact.executable != bool(executable):
                continue
            items.append(
                {
                    "id": artifact.id,
                    "type": artifact.type,
                    "owner": artifact.owner,
                    "created_by": artifact.created_by,
                    "executable": artifact.executable,
                    "content_size": len(artifact.content),
                    "code_preview": artifact.code[:220] if artifact.code else "",
                }
            )

        total = len(items)
        items = items[offset : offset + limit]
        return {
            "success": True,
            "query_type": "artifacts",
            "total": total,
            "returned": len(items),
            "results": items,
        }

    def _query_artifact(self, params: dict[str, Any]) -> dict[str, Any]:
        artifact_id = params.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            return {"success": False, "error": "artifact_id required", "error_code": "missing_param"}
        artifact = self.world.artifacts.get(artifact_id)
        if artifact is None:
            return {"success": False, "error": "artifact not found", "error_code": "not_found"}
        return {"success": True, "query_type": "artifact", "result": artifact.to_dict(include_code=False)}

    def _query_principals(self, params: dict[str, Any]) -> dict[str, Any]:
        limit = int(params.get("limit", 100))
        principals = list(self.world.ledger.get_all_scrip().keys())[:limit]
        return {
            "success": True,
            "query_type": "principals",
            "total": len(self.world.ledger.get_all_scrip()),
            "returned": len(principals),
            "results": principals,
        }

    def _query_principal(self, params: dict[str, Any]) -> dict[str, Any]:
        principal_id = params.get("principal_id")
        if not isinstance(principal_id, str) or not principal_id:
            return {"success": False, "error": "principal_id required", "error_code": "missing_param"}
        exists = self.world.ledger.principal_exists(principal_id)
        return {
            "success": True,
            "query_type": "principal",
            "exists": exists,
            "principal_id": principal_id,
            "scrip": self.world.ledger.get_scrip(principal_id) if exists else 0,
            "resources": self.world.ledger.get_all_resources(principal_id) if exists else {},
        }

    def _query_balances(self, params: dict[str, Any]) -> dict[str, Any]:
        principal_id = params.get("principal_id")
        if isinstance(principal_id, str) and principal_id:
            if not self.world.ledger.principal_exists(principal_id):
                return {"success": False, "error": "principal not found", "error_code": "not_found"}
            return {
                "success": True,
                "query_type": "balances",
                "principal_id": principal_id,
                "scrip": self.world.ledger.get_scrip(principal_id),
            }
        return {
            "success": True,
            "query_type": "balances",
            "balances": self.world.ledger.get_all_scrip(),
        }

    def _query_resources(self, params: dict[str, Any]) -> dict[str, Any]:
        principal_id = params.get("principal_id")
        if not isinstance(principal_id, str) or not principal_id:
            return {"success": False, "error": "principal_id required", "error_code": "missing_param"}
        resource = params.get("resource")
        resources = {
            "llm_budget": self.world.ledger.get_llm_budget(principal_id),
            "disk_used": self.world.artifacts.get_owner_usage(principal_id),
            "cpu_seconds_remaining": self.world.ledger.get_resource_remaining(principal_id, "cpu_seconds"),
            "llm_calls_remaining": self.world.ledger.get_resource_remaining(principal_id, "llm_calls"),
            "llm_tokens_remaining": self.world.ledger.get_resource_remaining(principal_id, "llm_tokens"),
        }
        if isinstance(resource, str) and resource:
            if resource not in resources:
                return {"success": False, "error": f"resource '{resource}' not found", "error_code": "not_found"}
            return {"success": True, "query_type": "resources", "resource": resource, "data": resources[resource]}
        return {"success": True, "query_type": "resources", "resources": resources}

    def _query_quotas(self, params: dict[str, Any]) -> dict[str, Any]:
        principal_id = params.get("principal_id")
        if not isinstance(principal_id, str) or not principal_id:
            return {"success": False, "error": "principal_id required", "error_code": "missing_param"}
        quotas = self.world.get_principal_quotas(principal_id)
        resource = params.get("resource")
        if isinstance(resource, str) and resource:
            data = quotas.get(resource)
            if data is None:
                return {"success": False, "error": "quota not found", "error_code": "not_found"}
            return {"success": True, "query_type": "quotas", "resource": resource, "data": data}
        return {"success": True, "query_type": "quotas", "quotas": quotas}

    def _query_mint(self, params: dict[str, Any]) -> dict[str, Any]:
        limit = int(params.get("limit", 10))
        return {
            "success": True,
            "query_type": "mint",
            "status": self.world.mint_auction.status() if self.world.mint_auction else {"phase": "disabled"},
            "submissions": self.world.mint_auction.get_submissions() if self.world.mint_auction else [],
            "history": self.world.mint_auction.get_history(limit=limit) if self.world.mint_auction else [],
        }

    def _query_events(self, params: dict[str, Any]) -> dict[str, Any]:
        limit = int(params.get("limit", 50))
        return {
            "success": True,
            "query_type": "events",
            "events": self.world.logger.read_recent(limit),
        }

    def _query_frozen(self, params: dict[str, Any]) -> dict[str, Any]:
        agent_id = params.get("agent_id")
        if isinstance(agent_id, str) and agent_id:
            return {
                "success": True,
                "query_type": "frozen",
                "agent_id": agent_id,
                "frozen": self.world.is_agent_frozen(agent_id),
            }
        frozen = [pid for pid in self.world.ledger.get_all_scrip() if self.world.is_agent_frozen(pid)]
        return {"success": True, "query_type": "frozen", "frozen_agents": frozen}

    def _query_libraries(self, params: dict[str, Any]) -> dict[str, Any]:
        principal_id = params.get("principal_id")
        if not isinstance(principal_id, str) or not principal_id:
            return {"success": False, "error": "principal_id required", "error_code": "missing_param"}
        return {
            "success": True,
            "query_type": "libraries",
            "principal_id": principal_id,
            "libraries": self.world.installed_libraries.get(principal_id, []),
        }

    def _query_dependencies(self, params: dict[str, Any]) -> dict[str, Any]:
        artifact_id = params.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id:
            return {"success": False, "error": "artifact_id required", "error_code": "missing_param"}
        artifact = self.world.artifacts.get(artifact_id)
        if artifact is None:
            return {"success": False, "error": "artifact not found", "error_code": "not_found"}
        dependents = [
            a.id
            for a in self.world.artifacts.artifacts.values()
            if not a.deleted and artifact_id in a.depends_on
        ]
        return {
            "success": True,
            "query_type": "dependencies",
            "artifact_id": artifact_id,
            "depends_on": artifact.depends_on,
            "dependents": dependents,
        }
