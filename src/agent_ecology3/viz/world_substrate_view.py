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
import re
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

RULE_READ_TASK = "ae3.agent.read_task"
RULE_PAID_READ = "ae3.market.paid_read"
RULE_TRANSFER = "ae3.market.transfer"
RULE_WRITE = "ae3.agent.write"
RULE_SOLVED = "ae3.mint.task_solved"
RULE_UNPAID = "ae3.mint.submission_unpaid"
RULE_NOTE = "ae3.agent.note"
RULE_ROYALTY = "ae3.mint.royalty"
RULE_MESSAGE = "ae3.agent.message"
# Plan 27 shared project.
RULE_INTEGRATED = "ae3.project.integrated"
RULE_REJECTED = "ae3.project.rejected"
RULE_JUDGED = "ae3.aes.judged"
RULE_BOUNTY = "ae3.aes.bounty"

BOARD, MARKET, CHECKER, PROJECT = "task-board", "market", "checker", "project"
PROJECT_EVENTS = {"change_integrated", "change_rejected", "aes_judged", "bounty_paid"}
NOTE_CHARS = 180


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


def build_projection(
    events: list[dict[str, Any]],
    *,
    run_id: str,
    principals: list[str],
    task_ids: list[str],
    starting_scrip: int,
) -> dict[str, Any]:
    """Build a live-projection/v0 bundle from AE3 canonical events.

    The world is a small place: a task board, a market and the checker's desk,
    with one workbench per agent. Reading a task, buying, and submitting are
    events at those places; each resident agent's end-of-turn note becomes a
    public message (World Substrate information + delivery) so it shows as a
    bubble.
    """
    world: dict[str, Any] = {"world_id": f"ae3-{run_id}", "revision": 0, "tick": 0, "entities": {}}
    for principal in principals:
        world["entities"][principal] = {
            "entity_id": principal,
            "components": {"member": {"scrip": starting_scrip, "solved": 0, "bought": 0, "sold": 0, "doing": "idle"}},
        }
    for principal in principals:
        world["entities"][f"bench-{principal}"] = {
            "entity_id": f"bench-{principal}",
            "components": {"workbench": {"owner": principal, "notes": 0}},
        }
    world["entities"][BOARD] = {
        "entity_id": BOARD,
        "components": {"resource": {"current": 0, "required": len(task_ids), "unit": "solved", "last_solved": None}},
    }
    world["entities"][MARKET] = {
        "entity_id": MARKET,
        "components": {"market": {"sales": 0, "scrip_moved": 0}},
    }
    world["entities"][CHECKER] = {
        "entity_id": CHECKER,
        "components": {"checker": {"passed": 0, "failed_or_unpaid": 0, "last_result": None}},
    }
    if any(e.get("event_type") in PROJECT_EVENTS for e in events):
        world["entities"][PROJECT] = {
            "entity_id": PROJECT,
            "components": {"project": {"integrated": 0, "rejected": 0, "criteria_met": 0, "last": None}},
        }
    initial = {"schema_version": "world-substrate-snapshot/v1", "world": deepcopy(world)}
    projected: list[dict[str, Any]] = []

    def emit(rule_id: str, source: dict[str, Any], updates: list[tuple[str, Any]], *, actor_id: str | None = None) -> None:
        # Living Scene binds visuals by exact rule id, and actor.move_to names
        # its actor, so actor-scoped events carry the actor in the rule id.
        if actor_id is not None:
            rule_id = f"{rule_id}.{actor_id}"
        changes = [
            {"path": "revision", "before": world["revision"], "after": world["revision"] + 1},
            {"path": "tick", "before": world["tick"], "after": world["tick"] + 1},
        ]
        world["revision"] += 1
        world["tick"] += 1
        for path, after in updates:
            parent, _, leaf = path.rpartition(".")
            container = _get(world, parent)
            before = deepcopy(container.get(leaf)) if isinstance(container, dict) else None
            if before == after:
                continue
            changes.append({"path": path, "before": before, "after": deepcopy(after)})
            _set(world, path, deepcopy(after))
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

    def value(path: str) -> Any:
        return _get(world, path)

    notes = 0
    for event in events:
        kind = event.get("event_type")
        actor = event.get("principal_id")
        if kind == "artifact_read" and actor in principals:
            seller = event.get("recipient")
            price = int(float(event.get("read_price_paid", 0) or 0))
            if price > 0 and seller in principals and seller != actor:
                emit(RULE_PAID_READ, event, actor_id=actor, updates=[
                    (member(actor, "scrip"), value(member(actor, "scrip")) - price),
                    (member(actor, "bought"), value(member(actor, "bought")) + 1),
                    (member(actor, "doing"), f"bought {event.get('artifact_id')} from {seller}"),
                    (member(seller, "scrip"), value(member(seller, "scrip")) + price),
                    (member(seller, "sold"), value(member(seller, "sold")) + 1),
                    (f"entities.{MARKET}.components.market.sales", value(f"entities.{MARKET}.components.market.sales") + 1),
                    (f"entities.{MARKET}.components.market.scrip_moved",
                     value(f"entities.{MARKET}.components.market.scrip_moved") + price),
                ])
            elif "_task_" in str(event.get("artifact_id")):
                emit(RULE_READ_TASK, event, actor_id=actor, updates=[(member(actor, "doing"), f"reading {event.get('artifact_id')}")])
        elif kind == "artifact_written" and actor in principals and event.get("was_update") is not True:
            if str(event.get("artifact_type", "")).startswith("solution:"):
                emit(RULE_WRITE, event, actor_id=actor, updates=[(member(actor, "doing"), f"writing {event.get('artifact_type')}")])
        elif kind == "transfer":
            sender, recipient = event.get("sender"), event.get("recipient")
            amount = int(event.get("amount", 0) or 0)
            if sender in principals and recipient in principals and sender != recipient and amount > 0:
                emit(RULE_TRANSFER, event, actor_id=sender, updates=[
                    (member(sender, "scrip"), value(member(sender, "scrip")) - amount),
                    (member(recipient, "scrip"), value(member(recipient, "scrip")) + amount),
                    (member(sender, "doing"), f"paid {amount} to {recipient}"),
                ])
        elif kind == "task_bounty_scored" and actor in principals:
            scored_task = str(event.get("task_id"))
            if event.get("first_claim") is True:
                minted = int(event.get("scrip_minted", 0) or 0)
                emit(RULE_SOLVED, event, actor_id=actor, updates=[
                    (f"entities.{BOARD}.components.resource.current", value(f"entities.{BOARD}.components.resource.current") + 1),
                    (f"entities.{BOARD}.components.resource.last_solved", f"{scored_task} by {actor}"),
                    (f"entities.{CHECKER}.components.checker.passed", value(f"entities.{CHECKER}.components.checker.passed") + 1),
                    (f"entities.{CHECKER}.components.checker.last_result", f"{scored_task}: passed"),
                    (member(actor, "scrip"), value(member(actor, "scrip")) + minted),
                    (member(actor, "solved"), value(member(actor, "solved")) + 1),
                    (member(actor, "doing"), f"solved {scored_task} (+{minted} scrip)"),
                ])
            else:
                outcome = "already claimed" if event.get("passed") else "failed hidden tests"
                emit(RULE_UNPAID, event, actor_id=actor, updates=[
                    (f"entities.{CHECKER}.components.checker.failed_or_unpaid",
                     value(f"entities.{CHECKER}.components.checker.failed_or_unpaid") + 1),
                    (f"entities.{CHECKER}.components.checker.last_result", f"{scored_task}: {outcome}"),
                    (member(actor, "doing"), f"{scored_task}: {outcome}"),
                ])
        elif kind in ("change_integrated", "change_rejected") and actor in principals:
            project = f"entities.{PROJECT}.components.project"
            if kind == "change_integrated":
                files = ", ".join(str(f).rsplit("/", 1)[-1] for f in event.get("files") or [])
                emit(RULE_INTEGRATED, event, actor_id=actor, updates=[
                    (f"{project}.integrated", value(f"{project}.integrated") + 1),
                    (f"{project}.last", f"{agent_label(str(actor))} integrated {files}"),
                    (member(actor, "doing"), f"integrated {files} into the project"),
                ])
            else:
                emit(RULE_REJECTED, event, actor_id=actor, updates=[
                    (f"{project}.rejected", value(f"{project}.rejected") + 1),
                    (member(actor, "doing"), "change rejected: " + str(event.get("reason") or "")[:80]),
                ])
        elif kind == "aes_judged" and actor in principals:
            rows = event.get("standings") or []
            moved = [f"{r.get('criterion_id')}: {str(r.get('before')).lower()} → {str(r.get('after')).lower()}"
                     for r in rows if r.get("before") != r.get("after")]
            project = f"entities.{PROJECT}.components.project"
            emit(RULE_JUDGED, event, actor_id=actor, updates=[
                (f"{project}.criteria_met", sum(1 for r in rows if r.get("after") == "SUPPORTED")),
                (f"{project}.last", "AES: " + ("; ".join(moved) or "no criterion changed")),
            ])
        elif kind == "bounty_paid" and actor in principals:
            share = int(event.get("share", 0) or 0)
            criterion = str(event.get("criterion_id"))
            notes += 1
            info_id, delivery_id = f"bounty-{notes}", f"bounty-{notes}-delivery"
            emit(RULE_BOUNTY, event, actor_id=actor, updates=[
                (member(actor, "scrip"), value(member(actor, "scrip")) + share),
                (member(actor, "doing"), f"paid {share} for {criterion} (AES evidence)"),
                (f"entities.{info_id}", {
                    "entity_id": info_id, "category_ids": ["information"],
                    "components": {"information": {
                        "active": True, "channel_id": "bounty",
                        "content": f"{criterion} met: +{share} scrip to {agent_label(str(actor))}",
                        "derived_from_info_id": None, "source_id": PROJECT,
                        "topic": "bounty", "visibility": "public",
                    }},
                }),
                (f"entities.{delivery_id}", {
                    "entity_id": delivery_id, "category_ids": ["delivery"],
                    "components": {"delivery": {
                        "channel_id": "bounty", "delivered_tick": world["tick"] + 1,
                        "info_id": info_id, "recipient_id": actor, "status": "delivered",
                    }},
                }),
            ])
        elif kind == "royalty_paid" and actor in principals:
            amount = int(event.get("amount", 0) or 0)
            solver = str(event.get("solver"))
            helper = (str(event.get("function")) if event.get("source") == "pilot_function_call"
                      else str(event.get("dependency_task_id")).rsplit("/", 1)[-1])
            notes += 1
            info_id, delivery_id = f"royalty-{notes}", f"royalty-{notes}-delivery"
            # A public message from the reusing agent to the helper's author, so
            # the view shows who reused whose code (line + bubble at the author).
            emit(RULE_ROYALTY, event, actor_id=actor, updates=[
                (member(actor, "scrip"), value(member(actor, "scrip")) + amount),
                (member(actor, "doing"), f"earned {amount} royalty: {solver} reused {helper}"),
                (f"entities.{info_id}", {
                    "entity_id": info_id, "category_ids": ["information"],
                    "components": {"information": {
                        "active": True, "channel_id": "royalty",
                        "content": f"{solver.replace('alpha_', 'Agent ')} reused your {helper}: +{amount} scrip",
                        "derived_from_info_id": None,
                        "source_id": solver if solver in principals else actor,
                        "topic": "royalty", "visibility": "public",
                    }},
                }),
                (f"entities.{delivery_id}", {
                    "entity_id": delivery_id, "category_ids": ["delivery"],
                    "components": {"delivery": {
                        "channel_id": "royalty", "delivered_tick": world["tick"] + 1,
                        "info_id": info_id, "recipient_id": actor, "status": "delivered",
                    }},
                }),
            ])
        elif kind == "agent_message" and actor in principals and str(event.get("recipient")) in principals:
            recipient = str(event.get("recipient"))
            text = " ".join(str(event.get("text") or "").split())
            notes += 1
            info_id, delivery_id = f"message-{notes}", f"message-{notes}-delivery"
            emit(RULE_MESSAGE, event, actor_id=actor, updates=[
                (member(actor, "doing"), f"messaged {recipient.replace('alpha_', 'Agent ')}"),
                (f"entities.{info_id}", {
                    "entity_id": info_id, "category_ids": ["information"],
                    "components": {"information": {
                        "active": True, "channel_id": "message",
                        "content": text[:240] + ("…" if len(text) > 240 else ""),
                        "derived_from_info_id": None, "source_id": actor,
                        "topic": "message", "visibility": "public",
                    }},
                }),
                (f"entities.{delivery_id}", {
                    "entity_id": delivery_id, "category_ids": ["delivery"],
                    "components": {"delivery": {
                        "channel_id": "message", "delivered_tick": world["tick"] + 1,
                        "info_id": info_id, "recipient_id": recipient, "status": "delivered",
                    }},
                }),
            ])
        elif kind == "resident_turn" and actor in principals:
            text = " ".join(str(event.get("note") or "").split())
            if not text:
                continue
            notes += 1
            info_id, delivery_id = f"note-{notes}", f"note-{notes}-delivery"
            bench_notes = f"entities.bench-{actor}.components.workbench.notes"
            emit(RULE_NOTE, event, actor_id=actor, updates=[
                (f"entities.{info_id}", {
                    "entity_id": info_id,
                    "category_ids": ["information"],
                    "components": {"information": {
                        "active": True, "channel_id": "note", "content": text[:NOTE_CHARS] + ("…" if len(text) > NOTE_CHARS else ""),
                        "derived_from_info_id": None, "source_id": actor, "topic": f"turn {event.get('turn')}",
                        "visibility": "public",
                    }},
                }),
                (f"entities.{delivery_id}", {
                    "entity_id": delivery_id,
                    "category_ids": ["delivery"],
                    "components": {"delivery": {
                        "channel_id": "note", "delivered_tick": world["tick"], "info_id": info_id,
                        "recipient_id": f"bench-{actor}", "status": "delivered",
                    }},
                }),
                (bench_notes, value(bench_notes) + 1),
                (member(actor, "doing"), "back at the workbench, writing a note"),
            ])

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


def principal_order(principal: str) -> tuple[Any, ...]:
    """Number order for agent ids: alpha_2 before alpha_10 (text order put
    alpha_10..alpha_16 between alpha_1 and alpha_2 in the 16-agent run)."""
    return tuple(int(part) if part.isdigit() else part for part in re.split(r"(\d+)", principal))


def agent_label(principal: str) -> str:
    return principal.replace("alpha_", "Agent ")


def build_profile(bundle: dict[str, Any], *, principals: list[str], task_ids: list[str]) -> dict[str, Any]:
    """Automatic living-scene/v1 profile: a place with three stations and workbenches."""
    principals = sorted(principals, key=principal_order)
    actors = {
        principal: {
            "entity": principal,
            "asset": "agent",
            "label": agent_label(principal),
            "home": home,
            "bindings": {
                "scrip": "components.member.scrip",
                "solved": "components.member.solved",
                "bought": "components.member.bought",
                "sold": "components.member.sold",
                "doing": "components.member.doing",
            },
            "render": {"inspector_fields": ["doing", "scrip", "solved", "bought", "sold"]},
        }
        for principal, home in zip(principals, _spread(len(principals), y=58.0, left=9.0, right=91.0), strict=True)
    }
    stations = {
        BOARD: {
            "entity": BOARD, "asset": "board", "label": "Task board", "home": [18.0, 28.0],
            "bindings": {
                "current": "components.resource.current",
                "required": "components.resource.required",
                "unit": "components.resource.unit",
                "last_solved": "components.resource.last_solved",
            },
            "render": {"kind": "resource", "current_binding": "current", "required_binding": "required",
                       "unit_binding": "unit", "inspector_fields": ["current", "required", "last_solved"]},
        },
        MARKET: {
            "entity": MARKET, "asset": "market", "label": "Market", "home": [50.0, 28.0],
            "bindings": {"sales": "components.market.sales", "scrip_moved": "components.market.scrip_moved"},
            "render": {"inspector_fields": ["sales", "scrip_moved"]},
        },
        CHECKER: {
            "entity": CHECKER, "asset": "checker", "label": "Checker (hidden tests)", "home": [82.0, 28.0],
            "bindings": {
                "passed": "components.checker.passed",
                "failed_or_unpaid": "components.checker.failed_or_unpaid",
                "last_result": "components.checker.last_result",
            },
            "render": {"inspector_fields": ["passed", "failed_or_unpaid", "last_result"]},
        },
    }

    if PROJECT in bundle["initial_snapshot"]["world"]["entities"]:
        # Shared-project run (Plan 27): no task board or checker desk; agents
        # integrate at the project and AES pays from there.
        stations = {
            PROJECT: {
                "entity": PROJECT, "asset": "project", "label": "Project (judged by AES)", "home": [30.0, 28.0],
                "bindings": {
                    "integrated": "components.project.integrated",
                    "rejected": "components.project.rejected",
                    "criteria_met": "components.project.criteria_met",
                    "last": "components.project.last",
                },
                "render": {"inspector_fields": ["criteria_met", "integrated", "rejected", "last"]},
            },
            MARKET: {**stations[MARKET], "home": [70.0, 28.0]},
        }

    benches = {
        f"bench-{principal}": {
            # Named after its owner (an empty bench read "notes"), and no wider
            # than the agent's own "Agent N" tag: "Agent N's bench" overran its
            # neighbours at 16 agents (plan25_codeflow_run5).
            "entity": f"bench-{principal}", "asset": "bench", "label": agent_label(principal).replace("Agent ", "Bench "),
            "home": [bench_x, 72.0],
            "bindings": {"notes": "components.workbench.notes"},
            "render": {"inspector_fields": ["notes"]},
        }
        for principal, bench_x in zip(
            principals, (x for x, _ in _spread(len(principals), y=0.0, left=9.0, right=91.0)), strict=True
        )
    }

    def visual(principal: str, label: str, target: str | None, *, transmit: bool = False) -> dict[str, Any]:
        operations: list[dict[str, Any]] = []
        if transmit:
            operations.append({"op": "information.transmit", "delivery_from_changed_entities": True, "read_paths": {}})
        if target is not None:
            operations.append({"op": "actor.move_to", "actor": principal, "entity": target, "animation_ms": 450})
        operations.append({"op": "action.feedback", "read_paths": {}, "label": label})
        return {"label": label, "operations": operations}

    event_visuals: dict[str, Any] = {}
    for principal in principals:
        event_visuals[f"{RULE_READ_TASK}.{principal}"] = visual(principal, "reads a task", BOARD)
        event_visuals[f"{RULE_PAID_READ}.{principal}"] = visual(principal, "buys another agent's work", MARKET)
        event_visuals[f"{RULE_TRANSFER}.{principal}"] = visual(principal, "pays another agent", MARKET)
        event_visuals[f"{RULE_WRITE}.{principal}"] = visual(principal, "writes a solution", f"bench-{principal}")
        event_visuals[f"{RULE_SOLVED}.{principal}"] = visual(principal, "solution passed the hidden tests", CHECKER)
        event_visuals[f"{RULE_UNPAID}.{principal}"] = visual(principal, "submission earned nothing", CHECKER)
        event_visuals[f"{RULE_NOTE}.{principal}"] = visual(principal, "end-of-turn note", f"bench-{principal}", transmit=True)
        event_visuals[f"{RULE_MESSAGE}.{principal}"] = visual(principal, "sends a message to another agent", None, transmit=True)
        event_visuals[f"{RULE_INTEGRATED}.{principal}"] = visual(principal, "integrates a change into the project", PROJECT)
        event_visuals[f"{RULE_REJECTED}.{principal}"] = visual(principal, "change rejected (conflict or not allowed)", PROJECT)
        event_visuals[f"{RULE_JUDGED}.{principal}"] = visual(principal, "AES runs the tests on the new main", None)
        event_visuals[f"{RULE_BOUNTY}.{principal}"] = visual(
            principal, "paid a bounty: AES recorded a criterion as met", None, transmit=True
        )
        event_visuals[f"{RULE_ROYALTY}.{principal}"] = visual(
            principal, "earns a royalty: another agent reused its helper", None, transmit=True
        )

    return {
        "schema_version": "world-substrate-living-scene/v1",
        "scene_id": f"{bundle['world_id']}-automatic-v2",
        "world": bundle["world_id"],
        # Short title: the renderer's tick badge sits where a long title ends
        # (plan25_codeflow_run2 rendered as "plan25_codeflo…"); the run id
        # goes in the subtitle instead.
        "title": "Agent Ecology 3",
        "subtitle": f"Run {bundle['world_id'].removeprefix('ae3-')}. " + (
            "Agents build one shared project, integrate their changes at the project, and earn scrip when AES records a test module as met."
            if PROJECT in stations else
            "Agents read tasks at the board, buy each other's work at the market, and earn scrip when the checker's hidden tests pass."),
        "note": LABEL,
        "assets": {
            "agent": {"kind": "text", "value": "A"},
            "bench": {"kind": "text", "value": "✎"},
            "board": {"kind": "text", "value": "▤"},
            "market": {"kind": "text", "value": "⇄"},
            "checker": {"kind": "text", "value": "✓"},
            "project": {"kind": "text", "value": "⌂"},
        },
        "scene": {"aspect_ratio": "16 / 9", "autoplay_ms": 650, "mobile_min_height": 680,
                  "background": "#1b2532", "shell_background": "#111827"},
        "zones": {
            "stations": {"label": "Shared places", "rect": [4.0, 16.0, 92.0, 26.0], "anchor": [50.0, 28.0]},
            "workbenches": {"label": "Workbenches", "rect": [4.0, 48.0, 92.0, 30.0], "anchor": [50.0, 64.0]},
        },
        "actors": actors,
        "entities": {**stations, **benches},
        "activities": {},
        "institutions": {},
        "event_visuals": event_visuals,
        "state_styles": {},
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
    if refresh_seconds:
        # A live page rebuilds periodically; show the latest moment on each
        # rebuild instead of replaying from tick 0.
        banner += (
            "<script>window.addEventListener('load',()=>setTimeout(()=>{"
            "const s=document.getElementById('scrub');"
            "if(s){s.value=s.max;s.dispatchEvent(new Event('input'));}"
            "const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='Pause');"
            "if(b)b.click();},300));</script>"
        )
    page = page.replace("<head>", "<head>" + head_extra, 1) if head_extra else page
    return page.replace("</body>", banner + "</body>", 1)
