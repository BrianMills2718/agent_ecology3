"""Run resident agents (long-lived Claude Agent SDK sessions) in one AE3 world.

Each turn, every agent's session is resumed with a kernel-generated
observation; it acts only through the ae3_action MCP tool, which the kernel
executes and answers. The dashboard (with the Interactions tab) is served
from the same process. Any failed turn stops the run (no substitutes).

Example (4 agents, 3 turns, up to 4 actions per turn):
    uv run python scripts/run_resident_ecology.py --agents 4 --turns 3 \\
        --task-bank config/tasks/humaneval_scale_v1.jsonl --port 9080
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
from agent_ecology3.simulation.resident import (  # noqa: E402
    ResidentKernel,
    ResidentRunError,
    run_agent_turn,
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
            pid: {"turns": a.turns_taken, "session_ids": a.session_ids_seen}
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
    (data_dir / "run_receipt.json").write_text(json.dumps(receipt, indent=2, default=str) + "\n", encoding="utf-8")


async def _main(args: argparse.Namespace) -> int:
    import uvicorn
    from llm_client import acall_llm

    data_dir = Path(args.data_dir).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    world = World(_config(args, data_dir), run_id=args.run_id)
    _seed_task_bank(world, Path(args.task_bank).resolve())
    kernel = ResidentKernel(world, data_dir / "agents", actions_per_turn=args.actions_per_turn)
    app = create_app(world_provider=lambda: world)
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
    except ResidentRunError as exc:
        state, reason = "invalid", str(exc)
        print(json.dumps({"terminal": "invalid", "error": reason}), flush=True)
    finally:
        _write_receipt(data_dir, args, world, kernel, state, reason)
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
    parser.add_argument("--keep-serving", action="store_true", help="keep the dashboard up after the run")
    args = parser.parse_args()
    if args.data_dir is None:
        args.data_dir = str(Path.home() / ".local" / "state" / "agent_ecology3" / args.run_id)
    return asyncio.run(_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
