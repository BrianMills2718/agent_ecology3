"""Render AE3 runs in World Substrate's world-agnostic living view (viewer only).

AE3 emits a ``world-substrate-live-projection/v0`` bundle (initial snapshot plus
ordered events whose leaf ``changes`` replay to the final state and hash) and a
``world-substrate-living-scene/v1`` profile. World Substrate's own renderer,
taken read-only from the pinned revision, turns them into one HTML page.

Agreed with the World Substrate session (2026-10-05): pin the revision, never
edit World Substrate, and label the view truthfully: these are AE3
transitions, not World Substrate Engine commits.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from typing import Any

WORLD_SUBSTRATE_REPO = Path.home() / "code" / "world-substrate"
WORLD_SUBSTRATE_PIN = "33bd121"
CACHE_ROOT = Path.home() / ".cache" / "agent_ecology3"
LABEL = "Rendered with the World Substrate living view; outcomes from agent_ecology3."

RULE_PAID_READ = "ae3.market.paid_read"
RULE_TRANSFER = "ae3.market.transfer"
RULE_SOLVED = "ae3.mint.task_solved"
RULE_UNPAID = "ae3.mint.submission_unpaid"


def _material_hash(world: dict[str, Any]) -> str:
    """Same construction as World Substrate's ``World.material_hash``."""
    encoded = json.dumps(world, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _get(world: dict[str, Any], path: str) -> Any:
    node: Any = world
    for part in path.split("."):
        node = node[part]
    return node


def _set(world: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    node: Any = world
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value


def _task_entity_id(task_id: str) -> str:
    return "task-" + task_id.replace("/", "-")


def build_projection(
    events: list[dict[str, Any]],
    *,
    run_id: str,
    principals: list[str],
    task_ids: list[str],
    starting_scrip: int,
) -> dict[str, Any]:
    """Build a live-projection/v0 bundle from AE3 canonical events."""
    world: dict[str, Any] = {
        "world_id": f"ae3-{run_id}",
        "revision": 0,
        "tick": 0,
        "entities": {},
    }
    for principal in principals:
        world["entities"][principal] = {
            "entity_id": principal,
            "components": {"member": {"scrip": starting_scrip, "solved": 0, "bought": 0, "sold": 0}},
        }
    for task_id in task_ids:
        entity = _task_entity_id(task_id)
        world["entities"][entity] = {
            "entity_id": entity,
            "components": {"resource": {"current": 0, "required": 1, "unit": "", "solver": None}},
        }
    world["entities"]["mint"] = {
        "entity_id": "mint",
        "components": {"gate": {"status": "open", "approval_count": 0, "required_approvals": len(task_ids)}},
    }
    initial = {"schema_version": "world-substrate-snapshot/v1", "world": deepcopy(world)}

    projected: list[dict[str, Any]] = []

    def emit(rule_id: str, source: dict[str, Any], updates: list[tuple[str, Any]]) -> None:
        changes = [
            {"path": "revision", "before": world["revision"], "after": world["revision"] + 1},
            {"path": "tick", "before": world["tick"], "after": world["tick"] + 1},
        ]
        world["revision"] += 1
        world["tick"] += 1
        for path, after in updates:
            before = _get(world, path)
            if before == after:
                continue
            changes.append({"path": path, "before": before, "after": after})
            _set(world, path, after)
        projected.append(
            {
                "event_id": f"ae3-{len(projected) + 1}-{source.get('event_number', 0)}",
                "rule_id": rule_id,
                "status": "accepted",
                "tick": world["tick"],
                "world_revision": world["revision"],
                "changes": changes,
                "hash_after": _material_hash(world),
            }
        )

    def member(principal: str, field: str) -> str:
        return f"entities.{principal}.components.member.{field}"

    for event in events:
        kind = event.get("event_type")
        if kind == "artifact_read":
            buyer, seller = event.get("principal_id"), event.get("recipient")
            price = int(float(event.get("read_price_paid", 0) or 0))
            if price <= 0 or buyer == seller or buyer not in principals or seller not in principals:
                continue
            emit(RULE_PAID_READ, event, [
                (member(buyer, "scrip"), _get(world, member(buyer, "scrip")) - price),
                (member(buyer, "bought"), _get(world, member(buyer, "bought")) + 1),
                (member(seller, "scrip"), _get(world, member(seller, "scrip")) + price),
                (member(seller, "sold"), _get(world, member(seller, "sold")) + 1),
            ])
        elif kind == "transfer":
            sender, recipient = event.get("sender"), event.get("recipient")
            amount = int(event.get("amount", 0) or 0)
            if sender in principals and recipient in principals and sender != recipient and amount > 0:
                emit(RULE_TRANSFER, event, [
                    (member(sender, "scrip"), _get(world, member(sender, "scrip")) - amount),
                    (member(recipient, "scrip"), _get(world, member(recipient, "scrip")) + amount),
                ])
        elif kind == "task_bounty_scored":
            solver, scored_task = event.get("principal_id"), event.get("task_id")
            if solver not in principals:
                continue
            if event.get("first_claim") is True and scored_task in task_ids:
                entity = _task_entity_id(str(scored_task))
                minted = int(event.get("scrip_minted", 0) or 0)
                emit(RULE_SOLVED, event, [
                    (f"entities.{entity}.components.resource.current", 1),
                    (f"entities.{entity}.components.resource.solver", solver),
                    (member(solver, "scrip"), _get(world, member(solver, "scrip")) + minted),
                    (member(solver, "solved"), _get(world, member(solver, "solved")) + 1),
                    ("entities.mint.components.gate.approval_count",
                     _get(world, "entities.mint.components.gate.approval_count") + 1),
                ])
            else:
                emit(RULE_UNPAID, event, [])

    return {
        "schema_version": "world-substrate-live-projection/v0",
        "branch_id": "main",
        "world_id": world["world_id"],
        "initial_snapshot": initial,
        "events": projected,
        "projection_final_hash": projected[-1]["hash_after"] if projected else _material_hash(world),
    }


def _spread(count: int, *, y: float, left: float = 10.0, right: float = 90.0) -> list[list[float]]:
    if count <= 0:
        return []
    if count == 1:
        return [[50.0, y]]
    step = (right - left) / (count - 1)
    return [[round(left + i * step, 2), y] for i in range(count)]


def build_profile(bundle: dict[str, Any], *, principals: list[str], task_ids: list[str]) -> dict[str, Any]:
    """Automatic living-scene/v1 profile: agents on one row, tasks on two rows, the mint between."""
    actors = {
        principal: {
            "entity": principal,
            "asset": "agent",
            "label": principal,
            "home": home,
            "bindings": {
                "scrip": "components.member.scrip",
                "solved": "components.member.solved",
                "bought": "components.member.bought",
                "sold": "components.member.sold",
            },
            "render": {"inspector_fields": ["scrip", "solved", "bought", "sold"]},
        }
        for principal, home in zip(principals, _spread(len(principals), y=86.0), strict=True)
    }
    per_row = 10
    rows = [task_ids[i:i + per_row] for i in range(0, len(task_ids), per_row)]
    row_ys = [22.0 + i * (34.0 / max(1, len(rows))) for i in range(len(rows))]
    homes = [home for row, y in zip(rows, row_ys) for home in _spread(len(row), y=round(y, 2), left=8.0, right=92.0)]
    entities = {
        _task_entity_id(task_id): {
            "entity": _task_entity_id(task_id),
            "asset": "task",
            "label": task_id.split("/")[-1],
            "home": home,
            "bindings": {
                "current": "components.resource.current",
                "required": "components.resource.required",
                "unit": "components.resource.unit",
                "solver": "components.resource.solver",
            },
            "render": {
                "kind": "resource",
                "current_binding": "current",
                "required_binding": "required",
                "unit_binding": "unit",
                "inspector_fields": ["current", "solver"],
            },
        }
        for task_id, home in zip(task_ids, homes, strict=True)
    }
    feedback = lambda label: {"label": label, "operations": [{"op": "action.feedback", "read_paths": {}, "label": label}]}  # noqa: E731
    return {
        "schema_version": "world-substrate-living-scene/v1",
        "scene_id": f"{bundle['world_id']}-automatic-v1",
        "world": bundle["world_id"],
        "title": f"Agent Ecology 3 · {bundle['world_id'].removeprefix('ae3-')}",
        "subtitle": "Agents buy each other's work and earn scrip when an outside checker passes their solutions.",
        "note": LABEL,
        "assets": {
            "agent": {"kind": "text", "value": "●"},
            "task": {"kind": "text", "value": "▢"},
            "mint_marker": {"kind": "text", "value": "◎"},
        },
        "scene": {"aspect_ratio": "16 / 9", "autoplay_ms": 700, "mobile_min_height": 680},
        "zones": {
            "tasks": {"label": "Tasks", "rect": [4.0, 14.0, 92.0, 46.0], "anchor": [50.0, 37.0]},
            "agents": {"label": "Agents", "rect": [4.0, 76.0, 92.0, 20.0], "anchor": [50.0, 86.0]},
        },
        "actors": actors,
        "entities": entities,
        "activities": {},
        "institutions": {
            "mint": {
                "entity": "mint",
                "asset": "mint_marker",
                "label": "Mint (outside checker)",
                "anchor": [50.0, 67.0],
                "bindings": {
                    "status": "components.gate.status",
                    "support": "components.gate.approval_count",
                    "required": "components.gate.required_approvals",
                },
                "render": {
                    "status_binding": "status",
                    "support_binding": "support",
                    "required_binding": "required",
                    "inspector_fields": ["support", "required"],
                },
            }
        },
        "event_visuals": {
            RULE_PAID_READ: {
                "label": "paid read (buyer pays seller)",
                "operations": [
                    {"op": "information.transmit", "delivery_from_changed_entities": True, "read_paths": {}},
                    {"op": "action.feedback", "read_paths": {}, "label": "paid read"},
                ],
            },
            RULE_TRANSFER: feedback("scrip transfer"),
            RULE_SOLVED: feedback("task solved: hidden tests passed"),
            RULE_UNPAID: feedback("submission earned nothing (failed or already claimed)"),
        },
        "state_styles": {"open": "positive"},
        "presentation": {},
    }


def pinned_renderer(pin: str = WORLD_SUBSTRATE_PIN) -> Path:
    """Read-only copy of World Substrate's renderer at the pinned revision.

    Uses ``git archive`` so the World Substrate repository is never modified.
    """
    target = CACHE_ROOT / f"world-substrate-{pin}"
    script = target / "scripts" / "render_composed_living_scene.py"
    if script.is_file():
        return script
    archive = subprocess.run(
        ["git", "-C", str(WORLD_SUBSTRATE_REPO), "archive", "--format=tar", pin, "scripts", "src"],
        capture_output=True,
        check=True,
    ).stdout
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=BytesIO(archive)) as tar:
        tar.extractall(target, filter="data")
    if not script.is_file():
        raise RuntimeError(f"pinned World Substrate {pin} has no composed renderer")
    return script


def render_living_view(bundle: dict[str, Any], profile: dict[str, Any], *, refresh_seconds: int | None = None) -> str:
    """Render one HTML page with World Substrate's renderer; fail loud on any error."""
    script = pinned_renderer()
    with tempfile.TemporaryDirectory(prefix="ae3_living_view_") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "projection.json").write_text(json.dumps(bundle), encoding="utf-8")
        (tmp_path / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
        out = tmp_path / "view.html"
        completed = subprocess.run(
            [sys.executable, str(script), str(tmp_path / "projection.json"),
             "--profile", str(tmp_path / "profile.json"), "--output", str(out)],
            capture_output=True, text=True, check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"World Substrate renderer failed: {completed.stderr.strip()[-800:]}")
        page = out.read_text(encoding="utf-8")
    banner = (
        "<div style=\"position:fixed;left:0;right:0;bottom:0;z-index:99;padding:6px 12px;"
        "font:13px system-ui;background:#1f2937;color:#e5e7eb\">" + LABEL + "</div>"
    )
    head_extra = f"<meta http-equiv=\"refresh\" content=\"{int(refresh_seconds)}\">" if refresh_seconds else ""
    page = page.replace("<head>", "<head>" + head_extra, 1) if head_extra else page
    return page.replace("</body>", banner + "</body>", 1)
