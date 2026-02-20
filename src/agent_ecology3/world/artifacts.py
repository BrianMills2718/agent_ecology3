"""Artifact domain model and in-memory store."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Artifact:
    id: str
    type: str
    content: str
    created_by: str
    owner: str
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    executable: bool = False
    code: str = ""
    read_price: int = 0
    invoke_price: int = 0

    access_contract_id: str = "kernel_contract_freeware"
    metadata: dict[str, Any] = field(default_factory=dict)
    interface: dict[str, Any] | None = None
    auth_state: dict[str, Any] = field(default_factory=dict)

    has_standing: bool = False
    has_loop: bool = False
    capabilities: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)

    deleted: bool = False
    deleted_at: str | None = None
    deleted_by: str | None = None

    kernel_protected: bool = False

    def to_dict(self, include_code: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "created_by": self.created_by,
            "owner": self.owner,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "executable": self.executable,
            "read_price": self.read_price,
            "invoke_price": self.invoke_price,
            "access_contract_id": self.access_contract_id,
            "metadata": self.metadata,
            "interface": self.interface,
            "auth_state": self.auth_state,
            "has_standing": self.has_standing,
            "has_loop": self.has_loop,
            "capabilities": list(self.capabilities),
            "depends_on": list(self.depends_on),
            "deleted": self.deleted,
            "deleted_at": self.deleted_at,
            "deleted_by": self.deleted_by,
            "kernel_protected": self.kernel_protected,
        }
        if include_code:
            data["code"] = self.code
        return data


@dataclass
class WriteResult:
    success: bool
    message: str
    data: dict[str, Any] | None = None


class ArtifactStore:
    def __init__(self) -> None:
        self.artifacts: dict[str, Artifact] = {}

    def get(self, artifact_id: str) -> Artifact | None:
        return self.artifacts.get(artifact_id)

    def count(self) -> int:
        return len(self.artifacts)

    def list_all(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        artifacts = list(self.artifacts.values())
        if not include_deleted:
            artifacts = [a for a in artifacts if not a.deleted]
        return [a.to_dict(include_code=False) for a in artifacts]

    def write(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        created_by: str,
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
        depends_on: list[str] | None = None,
        owner: str | None = None,
    ) -> Artifact:
        now = utc_now()
        existing = self.artifacts.get(artifact_id)
        if existing is None:
            artifact = Artifact(
                id=artifact_id,
                type=artifact_type,
                content=content,
                created_by=created_by,
                owner=owner or created_by,
                created_at=now,
                updated_at=now,
                executable=executable,
                code=code,
                read_price=read_price,
                invoke_price=invoke_price,
                access_contract_id=access_contract_id or "kernel_contract_freeware",
                metadata=metadata or {},
                interface=interface,
                auth_state={},
                has_standing=has_standing or has_loop,
                has_loop=has_loop,
                capabilities=capabilities or [],
                depends_on=depends_on or [],
            )
            artifact.auth_state.setdefault("writer", artifact.owner)
            artifact.auth_state.setdefault("principal", artifact.owner)
            self.artifacts[artifact_id] = artifact
            return artifact

        if existing.deleted:
            raise ValueError(f"artifact '{artifact_id}' is deleted")

        existing.type = artifact_type
        existing.content = content
        existing.updated_at = now
        existing.executable = executable
        existing.code = code
        existing.read_price = read_price
        existing.invoke_price = invoke_price
        existing.metadata = metadata or existing.metadata
        existing.interface = interface if interface is not None else existing.interface
        existing.has_standing = has_standing or existing.has_standing
        existing.has_loop = has_loop or existing.has_loop
        existing.capabilities = list(capabilities or existing.capabilities)
        existing.depends_on = list(depends_on or existing.depends_on)
        if access_contract_id:
            existing.access_contract_id = access_contract_id
        if owner is not None:
            existing.owner = owner
            existing.auth_state["writer"] = owner
            existing.auth_state.setdefault("principal", owner)
        return existing

    def edit_artifact(self, artifact_id: str, old_string: str, new_string: str) -> WriteResult:
        artifact = self.get(artifact_id)
        if artifact is None:
            return WriteResult(False, f"artifact '{artifact_id}' not found", {"error": "not_found"})
        if artifact.deleted:
            return WriteResult(False, f"artifact '{artifact_id}' is deleted", {"error": "deleted"})
        hits = artifact.content.count(old_string)
        if hits == 0:
            return WriteResult(False, "old_string not found in artifact content", {"error": "not_found_in_content"})
        if hits > 1:
            return WriteResult(False, "old_string is not unique in artifact content", {"error": "not_unique"})
        updated = artifact.content.replace(old_string, new_string, 1)
        if updated == artifact.content:
            return WriteResult(False, "edit produced no change", {"error": "no_change"})
        artifact.content = updated
        artifact.updated_at = utc_now()
        return WriteResult(True, "artifact updated", {"artifact_id": artifact_id})

    def soft_delete(self, artifact_id: str, deleted_by: str) -> bool:
        artifact = self.get(artifact_id)
        if artifact is None or artifact.deleted:
            return False
        artifact.deleted = True
        artifact.deleted_at = utc_now()
        artifact.deleted_by = deleted_by
        artifact.updated_at = artifact.deleted_at
        return True

    def get_artifacts_by_owner(self, owner: str) -> list[str]:
        return [a.id for a in self.artifacts.values() if not a.deleted and a.owner == owner]

    def get_owner_usage(self, owner: str) -> int:
        total = 0
        for artifact in self.artifacts.values():
            if artifact.deleted or artifact.owner != owner:
                continue
            total += len(artifact.content.encode("utf-8"))
            total += len(artifact.code.encode("utf-8"))
        return total

    def discover_loops(self) -> list[str]:
        return [
            artifact.id
            for artifact in self.artifacts.values()
            if artifact.has_loop and artifact.executable and not artifact.deleted
        ]

    def transfer_ownership(self, artifact_id: str, new_owner: str) -> bool:
        artifact = self.get(artifact_id)
        if artifact is None or artifact.deleted:
            return False
        artifact.owner = new_owner
        artifact.auth_state["writer"] = new_owner
        artifact.auth_state["principal"] = new_owner
        artifact.updated_at = utc_now()
        return True

    def modify_protected_content(self, artifact_id: str, *, content: str) -> bool:
        artifact = self.get(artifact_id)
        if artifact is None:
            return False
        artifact.content = content
        artifact.updated_at = utc_now()
        return True
