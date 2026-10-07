"""Scripted shared-project run on the Plan 27 pilot (no model calls).

Four scripted agents act through the real kernel (``ResidentKernel.act``),
real git and the real ``aes`` CLI on a run copy of the M1 tinydb pilot. Their
"work" is restoring files from the library's reference commit (taken from the
builder's cached clone, outside this repo), plus one deliberate conflict and
one deliberate break and repair, so every shared-project event appears. The
run directory holds an ordinary ``run_receipt.json`` and event log, so the
dashboard's review mode serves it:

    uv run python scripts/run_pilot_scripted.py --data-dir ~/.local/state/agent_ecology3/plan27_m2_scripted
    uv run python scripts/run_recoverable_evaluation.py review --data-dir ~/.local/state/agent_ecology3/plan27_m2_scripted --port 9096

Each step prints its own timing; each judge step's seconds are in the receipt.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from agent_ecology3.config import AppConfig, load_config  # noqa: E402
from agent_ecology3.simulation.pilot import PilotProject  # noqa: E402
from agent_ecology3.simulation.resident import ResidentKernel  # noqa: E402
from agent_ecology3.world import World  # noqa: E402
from scripts.build_aes_pilot import DEFAULT_CACHE, DEFAULT_DEST, REFERENCE_COMMIT  # noqa: E402
from scripts.run_resident_ecology import _write_receipt  # noqa: E402

_T0 = time.monotonic()


def log(message: str) -> None:
    print(f"[{time.monotonic() - _T0:7.1f}s] {message}", flush=True)


def reference(cache: Path, path: str) -> str:
    return subprocess.run(["git", "--git-dir", str(cache), "show", f"{REFERENCE_COMMIT}:{path}"],
                          capture_output=True, text=True, check=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pilot", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    data_dir = args.data_dir.expanduser().resolve()
    if data_dir.exists():
        raise SystemExit(f"{data_dir} exists; choose a new directory")
    run_id = args.run_id or data_dir.name
    config = load_config(REPO_ROOT / "config" / "config.yaml")
    config.principals.count = 4
    config.principals.starting_llm_budget = 1.0
    config.llm.enable_bootstrap_loop_llm = False
    config.logging.logs_dir = str(data_dir / "logs")
    config.logging.recent_event_limit = 5000
    config.mint.enabled = False
    config.economy.cross_principal_trading = True
    world = World(AppConfig.model_validate(config.model_dump()), run_id=run_id)
    log(f"cloning pilot {args.pilot} into {data_dir / 'pilot_project'}")
    pilot = PilotProject.create(
        args.pilot, data_dir / "pilot_project",
        {pid: data_dir / "agents" / pid / "work" for pid in world.principal_ids},
        royalty_scrip=world.config.mint.royalty_scrip,
    )
    kernel = ResidentKernel(world, data_dir / "agents", actions_per_turn=4, pilot=pilot)
    folder = {pid: kernel.agents[pid].workdir / "work" for pid in kernel.agents}
    cache = args.cache.expanduser()

    def restore(agent: str, *paths: str) -> None:
        for path in paths:
            (folder[agent] / path).write_text(reference(cache, path), encoding="utf-8")

    def edit(agent: str, path: str, old: str, new: str) -> None:
        file = folder[agent] / path
        text = file.read_text(encoding="utf-8")
        if old not in text:
            raise SystemExit(f"{old!r} not in {agent}'s {path}")
        file.write_text(text.replace(old, new, 1), encoding="utf-8")

    def act(agent: str, payload: dict[str, Any]) -> dict[str, Any]:
        started = time.monotonic()
        kernel.agents[agent].actions_this_turn = 0
        outcome = asyncio.run(kernel.act(kernel.agents[agent], payload))
        text = outcome.get("message") or outcome.get("error")
        log(f"turn {kernel.turn} {agent} {payload['action_type']}: {str(text)[:600]} ({time.monotonic() - started:.1f}s)")
        if kernel.fatal_error:
            raise SystemExit(kernel.fatal_error)
        return outcome

    def note(agent: str, text: str) -> None:
        world.logger.log("resident_turn", {
            "turn": kernel.turn, "principal_id": agent, "session_id": "scripted", "trace_id": "scripted",
            "actions": kernel.agents[agent].actions_this_turn, "num_turns": 0, "duration_ms": 0,
            "builtin_tool_calls": 0, "sandboxed_shell_commands": 0, "note": text,
            "finish_reason": "scripted", "cost": 0, "cost_source": "scripted",
        })
        kernel.agents[agent].turns_taken += 1

    propose = {"action_type": "propose_change"}
    kernel.turn = 1
    restore("alpha_1", "tinydb/utils.py")
    act("alpha_1", {**propose, "content": "utils from the spec"})
    restore("alpha_2", "tinydb/queries.py")
    act("alpha_2", {**propose, "content": "queries"})
    restore("alpha_3", "tinydb/utils.py")
    edit("alpha_3", "tinydb/utils.py", "class LRUCache", "class LRUCache  # alpha_3's version")
    act("alpha_3", {**propose, "content": "my own utils"})
    restore("alpha_4", "tinydb/storages.py", "tinydb/middlewares.py")
    act("alpha_4", {**propose, "content": "storages and middlewares"})
    act("alpha_4", {"action_type": "send_message", "recipient_id": "alpha_3",
                    "content": "utils is in main already; take main's version and do table.py?"})
    for agent in kernel.agents:
        note(agent, "scripted turn 1")

    kernel.turn = 2
    (folder["alpha_3"] / "tinydb/utils.py").write_text(
        subprocess.run(["git", "show", "main:tinydb/utils.py"], cwd=folder["alpha_3"], capture_output=True,
                       text=True, check=True).stdout, encoding="utf-8")
    restore("alpha_3", "tinydb/table.py")
    act("alpha_3", {**propose, "content": "resolved utils (took main), table"})
    restore("alpha_1", "tinydb/database.py", "tinydb/operations.py", "tinydb/version.py")
    act("alpha_1", {**propose, "content": "database, operations"})
    for agent in kernel.agents:
        note(agent, "scripted turn 2")

    kernel.turn = 3
    act("alpha_2", {**propose})  # nothing new: brings its folder up to date
    edit("alpha_2", "tinydb/operations.py", "doc[field] += n", "doc[field] -= n")
    act("alpha_2", {**propose, "content": "tweak add()"})
    act("alpha_4", {**propose})
    edit("alpha_4", "tinydb/operations.py", "doc[field] -= n", "doc[field] += n")
    act("alpha_4", {**propose, "content": "fix add(): it subtracted"})
    act("alpha_2", {"action_type": "transfer", "recipient_id": "alpha_4", "amount": 2, "memo": "thanks for the fix"})
    for agent in kernel.agents:
        note(agent, "scripted turn 3")

    args_ns = argparse.Namespace(model="scripted (no model)", run_id=run_id, agents=4, turns=3, aes_pilot=str(args.pilot))
    _write_receipt(data_dir, args_ns, world, kernel, "completed", "scripted run")
    receipt = json.loads((data_dir / "run_receipt.json").read_text())
    log("judge seconds: " + json.dumps(pilot.judge_seconds))
    log("standings: " + json.dumps(receipt["shared_project"]["standings"]))
    log("scrip: " + json.dumps({p: world.ledger.get_scrip(p) for p in world.principal_ids}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
