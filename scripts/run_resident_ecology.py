"""Run resident agents (long-lived Claude Agent SDK sessions) in one AE3 world.

Each turn, every agent's session is resumed with a kernel-generated
observation; it acts only through the ae3_action MCP tool, which the kernel
executes and answers. The dashboard (with the Interactions tab) is served
from the same process. Any failed turn stops the run (no substitutes).

Example (4 agents, 3 turns, up to 4 actions per turn):
    uv run python scripts/run_resident_ecology.py --agents 4 --turns 3 \\
        --task-bank config/tasks/humaneval_scale_v1.jsonl --port 9080

Plan 27 shared project instead of the task bank: the run clones the pilot
sandbox into <data dir>/pilot_project and gives each agent a git worktree of
it (its Codex folder); propose_change integrates, AES judges, bounties pay:
    uv run python scripts/run_resident_ecology.py --agents 4 --turns 20 \\
        --aes-pilot ~/.local/state/agent_ecology3/pilots/tinydb --port 9080
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from agent_ecology3.config import AppConfig, load_config  # noqa: E402
from agent_ecology3.dashboard.server import create_app  # noqa: E402
from agent_ecology3.simulation.pilot import PilotProject  # noqa: E402
from agent_ecology3.simulation.resident import (  # noqa: E402
    ResidentKernel,
    ResidentRunError,
    history_shell_commands,
    run_agent_turn,
    trim_codex_home,
)
from agent_ecology3.world import World  # noqa: E402
from scripts.run_recoverable_evaluation import _seed_task_bank  # noqa: E402


def _config(args: argparse.Namespace, data_dir: Path) -> AppConfig:
    config = load_config(REPO_ROOT / "config" / "config.yaml")
    config.principals.count = args.agents
    config.principals.starting_llm_budget = 1.0
    config.llm.enable_bootstrap_loop_llm = False
    config.llm.default_model = args.model
    config.logging.logs_dir = str(data_dir / "logs")
    config.logging.recent_event_limit = 5000
    if args.aes_pilot:
        # Shared project: AES evidence is the only oracle; the task-bank mint is off.
        config.mint.enabled = False
    else:
        config.mint.enabled = True
        config.mint.mode = "task_bounty"
        config.mint.task_bank_path = str(Path(args.task_bank).resolve())
    config.mint.scoring_max_budget = 0.0
    config.economy.cross_principal_trading = True
    return AppConfig.model_validate(config.model_dump())


def _write_receipt(data_dir: Path, args: argparse.Namespace, world: World, kernel: ResidentKernel,
                   state: str, reason: str | None) -> None:
    receipt = {
        "schema_version": "ae3_resident_run_receipt.v1",
        "acknowledgement": "plan25/resident-agents/v1",
        "model": args.model,
        "agents": {
            pid: {
                "turns": a.turns_taken,
                "session_ids": a.session_ids_seen,
                # Counted from the agent's own Codex thread history, not a counter.
                "shell_commands_from_history": history_shell_commands(a.codex_home),
            }
            for pid, a in kernel.agents.items()
        },
        "recovery": {
            "run_id": args.run_id,
            "committed_attempts": sum(a.turns_taken for a in kernel.agents.values()),
            "target_attempts": args.agents * args.turns,
            "lifecycle_state": state,
            "terminal_reason": reason,
        },
        "world_state": world.get_state_summary(event_limit=200),
    }
    if kernel.pilot is not None:
        pilot = kernel.pilot
        receipt["shared_project"] = {
            "sandbox": str(args.aes_pilot), "run_copy": str(pilot.root), "base_commit": pilot.base_commit,
            "bounty_scrip": pilot.bounty_scrip, "royalty_scrip": pilot.royalty_scrip,
            "integrations": len(pilot.integrations), "criteria_held": sorted(pilot.held),
            "standings": {c["criterion_id"]: c["standing"] for c in pilot.last_reconcile.get("criteria", [])},
            "judge_seconds": pilot.judge_seconds,
        }
    (data_dir / "run_receipt.json").write_text(json.dumps(receipt, indent=2, default=str) + "\n", encoding="utf-8")


async def _main(args: argparse.Namespace) -> int:
    import uvicorn
    from llm_client import acall_llm

    data_dir = Path(args.data_dir).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    world = World(_config(args, data_dir), run_id=args.run_id)
    pilot = None
    if args.aes_pilot:
        pilot = PilotProject.create(
            Path(args.aes_pilot), data_dir / "pilot_project",
            {pid: data_dir / "agents" / pid / "work" for pid in world.principal_ids},
            bounty_scrip=args.bounty_scrip, royalty_scrip=world.config.mint.royalty_scrip,
        )
        print(json.dumps({"shared_project": str(pilot.root), "base_commit": pilot.base_commit}), flush=True)
    else:
        _seed_task_bank(world, Path(args.task_bank).resolve())
    kernel = ResidentKernel(world, data_dir / "agents", actions_per_turn=args.actions_per_turn, pilot=pilot)
    # The Bounties tab reads the run's own copy, so it shows this run's standings.
    app = create_app(world_provider=lambda: world, pilot_path=str(pilot.root) if pilot else args.pilot)
    kernel.install_routes(app)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=args.port, log_level="warning"))
    serve_task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.1)
    kernel_url = f"http://127.0.0.1:{args.port}"
    print(json.dumps({"dashboard": kernel_url + "/", "run_id": args.run_id}), flush=True)
    state, reason = "completed", None
    try:
        for turn in range(1, args.turns + 1):
            kernel.turn = turn
            started = time.monotonic()
            results = await asyncio.gather(*[
                run_agent_turn(kernel, agent, model=args.model, kernel_url=kernel_url,
                               run_id=args.run_id, acall_llm=acall_llm,
                               reasoning_effort=args.reasoning_effort)
                for agent in kernel.agents.values()
            ])
            print(json.dumps({"turn": turn, "seconds": round(time.monotonic() - started, 1),
                              "actions": {r["principal_id"]: r["actions"] for r in results}}), flush=True)
            # Checkpoint each turn: plan25_codeflow_run3 was killed by a WSL
            # restart at turn 28 and, writing only at the end, left no receipt.
            _write_receipt(data_dir, args, world, kernel, "running", f"after turn {turn} of {args.turns}")
    except ResidentRunError as exc:
        state, reason = "invalid", str(exc)
        print(json.dumps({"terminal": "invalid", "error": reason}), flush=True)
    finally:
        _write_receipt(data_dir, args, world, kernel, state, reason)
        for agent in kernel.agents.values():
            trim_codex_home(agent.codex_home)
        if not args.keep_serving:
            server.should_exit = True
        await serve_task
    return 0 if state == "completed" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agents", type=int, default=4)
    parser.add_argument("--turns", type=int, default=3)
    parser.add_argument("--actions-per-turn", type=int, default=4)
    parser.add_argument("--model", default="codex/gpt-5.6-luna",
                        help="codex/<model> (ChatGPT subscription) or claude-code/<model> (Claude subscription)")
    parser.add_argument("--reasoning-effort", default="low", help="Codex reasoning effort")
    parser.add_argument("--task-bank", default=str(REPO_ROOT / "config" / "tasks" / "humaneval_scale_v1.jsonl"))
    parser.add_argument("--run-id", default=f"plan25_resident_{time.strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--port", type=int, default=9080)
    parser.add_argument("--pilot", default=None,
                        help="Plan 27 pilot sandbox whose open AES gaps the Bounties tab lists (env AE3_PILOT_PATH)")
    parser.add_argument("--aes-pilot", default=None,
                        help="Plan 27: run on this AES pilot sandbox (a copy is made per run) instead of the task bank")
    parser.add_argument("--bounty-scrip", type=int, default=30,
                        help="scrip a criterion pays, split among its contributors, when AES first records it met")
    parser.add_argument("--keep-serving", action="store_true", help="keep the dashboard up after the run")
    args = parser.parse_args()
    if args.data_dir is None:
        args.data_dir = str(Path.home() / ".local" / "state" / "agent_ecology3" / args.run_id)
    return asyncio.run(_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
