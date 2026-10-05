"""Strict structured-output contract for one Luna loop decision."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Annotated, Any, Literal, TypeAlias, cast

from pydantic import BaseModel, ConfigDict, Field

from .actions import ActionIntent, parse_intent_from_json

LUNA_MODEL = "codex/gpt-5.6-luna"
LUNA_RESPONSE_MODEL = "LunaLoopDecisionV1"
LUNA_SCHEMA_VERSION = "luna_loop_decision.v1"
REVIEWED_LLM_CLIENT_REVISION = "ea550d2d4b8463798d973d2899bc9ebf5e07201f"
LUNA_ACTION_TYPES = (
    "write_artifact",
    "read_artifact",
    "transfer",
    "transfer_resource",
    "submit_to_mint",
    "query_kernel",
)

LunaQueryType: TypeAlias = Literal[
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
]

LunaResourceType: TypeAlias = Literal[
    "llm_budget",
    "disk_quota",
    "llm_calls",
    "llm_tokens",
    "cpu_seconds",
]


class _StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LunaQueryParamsV1(_StrictContract):
    """Closed projection of the query keys currently consumed by the kernel."""

    owner: str | None = None
    type: str | None = None
    artifact_type: str | None = None
    artifact_id: str | None = None
    executable: bool | None = None
    limit: int | None = None
    offset: int | None = None
    principal_id: str | None = None
    readable_only: bool | None = None
    include_permissions: bool | None = None
    resource: str | None = None
    agent_id: str | None = None


class LunaWriteArtifactV1(_StrictContract):
    action_type: Literal["write_artifact"]
    artifact_id: str
    artifact_type: str
    content: str
    read_price: int | None = None
    invoke_price: int | None = None
    access_contract_id: str | None = None


class LunaReadArtifactV1(_StrictContract):
    action_type: Literal["read_artifact"]
    artifact_id: str


class LunaTransferV1(_StrictContract):
    action_type: Literal["transfer"]
    recipient_id: str
    amount: int
    memo: str | None = None


class LunaTransferResourceV1(_StrictContract):
    action_type: Literal["transfer_resource"]
    recipient_id: str
    resource: LunaResourceType
    amount: float
    memo: str | None = None


class LunaSubmitToMintV1(_StrictContract):
    action_type: Literal["submit_to_mint"]
    artifact_id: str
    bid: int


class LunaQueryKernelV1(_StrictContract):
    action_type: Literal["query_kernel"]
    query_type: LunaQueryType
    params: LunaQueryParamsV1


LunaActionV1: TypeAlias = Annotated[
    LunaWriteArtifactV1
    | LunaReadArtifactV1
    | LunaTransferV1
    | LunaTransferResourceV1
    | LunaSubmitToMintV1
    | LunaQueryKernelV1,
    Field(discriminator="action_type"),
]


class LunaLoopDecisionV1(_StrictContract):
    """Versioned provider envelope containing exactly one permitted action."""

    schema_version: Literal["luna_loop_decision.v1"]
    action: LunaActionV1

    def action_payload(self) -> dict[str, Any]:
        """Return the action shape consumed by AE3's existing action boundary."""

        return self.action.model_dump(mode="json", exclude_none=True)


def luna_provider_schema() -> dict[str, Any]:
    """Compile the exact provider schema through the shared Codex projector."""

    from llm_client.route_certification_runtime import codex_native_provider_schema

    return cast(dict[str, Any], codex_native_provider_schema(LunaLoopDecisionV1))


def luna_provider_schema_sha256() -> str:
    """Return a stable digest of the exact shared-client provider schema."""

    encoded = json.dumps(
        luna_provider_schema(),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def shared_client_exposes_codex_events() -> bool:
    """Return whether the public shared result declares Codex event custody."""

    from llm_client.core.data_types import LLMCallResult

    return "codex_events" in LLMCallResult.__dataclass_fields__


def shared_client_source_status() -> tuple[str | None, bool]:
    """Return the imported shared-client Git revision and clean-tree status."""

    try:
        import llm_client
    except Exception:  # noqa: BLE001 - any import failure makes the revision unprovable
        return None, False

    module_path = getattr(llm_client, "__file__", None)
    if not isinstance(module_path, str) or not module_path:
        return None, False
    location = Path(module_path).resolve().parent
    installed = _installed_vcs_revision(location)
    if installed is not None:
        # Installed from an immutable Git commit (PEP 610): the package files
        # cannot carry uncommitted edits, so the source is clean by construction.
        return installed, True
    try:
        root_result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=location,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None, False
    if root_result.returncode != 0 or not root_result.stdout.strip():
        return None, False
    root = Path(root_result.stdout.strip())
    if (root / "llm_client").resolve() != location:
        # The enclosing repository is not llm_client's own checkout (for
        # example a virtualenv inside another project's worktree).
        return None, False
    try:
        revision_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None, False
    revision: str | None = revision_result.stdout.strip()
    if revision_result.returncode != 0 or not revision:
        revision = None
    clean = status_result.returncode == 0 and not status_result.stdout.strip()
    return revision, clean


def _installed_vcs_revision(package_dir: Path) -> str | None:
    """Return the commit an installed llm-client was built from, if recorded.

    Only trusts a PEP 610 ``direct_url.json`` whose distribution owns
    ``package_dir``; editable or index installs return ``None``.
    """

    from importlib import metadata

    try:
        dist = metadata.distribution("llm-client")
    except metadata.PackageNotFoundError:
        return None
    raw = dist.read_text("direct_url.json")
    if not raw:
        return None
    try:
        direct_url = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(direct_url, dict) or direct_url.get("dir_info", {}).get("editable"):
        return None
    vcs_info = direct_url.get("vcs_info")
    if not isinstance(vcs_info, dict) or vcs_info.get("vcs") != "git":
        return None
    commit = vcs_info.get("commit_id")
    if not isinstance(commit, str) or len(commit) != 40:
        return None
    owned = Path(str(dist.locate_file("llm_client"))).resolve()
    if owned != package_dir:
        return None
    return commit


def validate_luna_action_for_principal(
    decision: LunaLoopDecisionV1,
    principal_id: str,
) -> tuple[dict[str, Any], ActionIntent]:
    """Feed a typed action through AE3's canonical semantic action parser."""

    action = decision.action_payload()
    parsed = parse_intent_from_json(
        principal_id,
        json.dumps(action, ensure_ascii=True, sort_keys=True),
    )
    if isinstance(parsed, str):
        raise TypeError(f"Luna action failed canonical AE3 parsing: {parsed}")
    return action, parsed
