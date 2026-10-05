"""Agent Ecology 3 command-line entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Literal, cast

from dotenv import load_dotenv

from .config import AppConfig, load_config
from .dashboard import create_app
from .simulation import SimulationRunner
from .world import World


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Agent Ecology 3")
    parser.add_argument("--config", default="config/config.yaml", help="Path to config YAML")
    parser.add_argument("--duration", type=float, default=None, help="Seconds to run simulation")
    parser.add_argument("--agents", type=int, default=None, help="Override principal count")
    parser.add_argument("--model", default=None, help="Override llm.default_model for this run")
    parser.add_argument(
        "--llm-loop",
        choices=("on", "off"),
        default=None,
        help="Override llm.enable_bootstrap_loop_llm (on/off)",
    )
    parser.add_argument(
        "--loop-llm-cooldown",
        type=float,
        default=None,
        help="Override llm.loop_llm_cooldown_seconds (set 0 to disable cooldown)",
    )
    parser.add_argument(
        "--loop-forced-explore",
        choices=("baseline", "reduced", "off"),
        default=None,
        help="Override llm.loop_forced_explore_mode",
    )
    parser.add_argument(
        "--loop-policy-seed",
        type=int,
        default=None,
        help="Override llm.loop_policy_seed",
    )
    parser.add_argument(
        "--loop-prompt-template",
        default=None,
        help="Override llm.loop_prompt_template_path",
    )
    parser.add_argument("--dashboard", action="store_true", help="Run simulation with dashboard server")
    parser.add_argument("--dashboard-only", action="store_true", help="Run dashboard only (read existing JSONL logs)")
    parser.add_argument("--host", default=None, help="Dashboard host override")
    parser.add_argument("--port", type=int, default=None, help="Dashboard port override")
    return parser.parse_args()


def _load_runtime_config(
    path: str,
    agents_override: int | None,
    model_override: str | None = None,
    llm_loop_override: str | None = None,
    loop_llm_cooldown_override: float | None = None,
    loop_forced_explore_override: str | None = None,
    loop_policy_seed_override: int | None = None,
    loop_prompt_template_override: str | None = None,
) -> AppConfig:
    config = load_config(path)
    if agents_override is not None:
        if agents_override <= 0:
            raise ValueError("--agents must be > 0")
        config.principals.count = agents_override
    if llm_loop_override is not None:
        normalized = str(llm_loop_override).strip().lower()
        if normalized == "on":
            config.llm.enable_bootstrap_loop_llm = True
        elif normalized == "off":
            config.llm.enable_bootstrap_loop_llm = False
        else:
            raise ValueError("--llm-loop must be one of: on, off")
    if model_override is not None:
        model = str(model_override).strip()
        if not model:
            raise ValueError("--model must be a non-empty string")
        config.llm.default_model = model
        if config.llm.allowed_models and model not in config.llm.allowed_models:
            config.llm.allowed_models.append(model)
    if loop_llm_cooldown_override is not None:
        if loop_llm_cooldown_override < 0:
            raise ValueError("--loop-llm-cooldown must be >= 0")
        config.llm.loop_llm_cooldown_seconds = float(loop_llm_cooldown_override)
    if loop_forced_explore_override is not None:
        normalized_mode = str(loop_forced_explore_override).strip().lower()
        if normalized_mode not in {"baseline", "reduced", "off"}:
            raise ValueError("--loop-forced-explore must be one of: baseline, reduced, off")
        config.llm.loop_forced_explore_mode = cast(Literal["baseline", "reduced", "off"], normalized_mode)
    if loop_policy_seed_override is not None:
        config.llm.loop_policy_seed = int(loop_policy_seed_override)
    if loop_prompt_template_override is not None:
        template_path = str(loop_prompt_template_override).strip()
        if not template_path:
            raise ValueError("--loop-prompt-template must be a non-empty string path")
        config.llm.loop_prompt_template_path = template_path
    return config


def _effective_duration(config: AppConfig, duration_override: float | None) -> float:
    if duration_override is not None:
        if duration_override <= 0:
            raise ValueError("--duration must be > 0")
        return duration_override
    return config.simulation.default_duration_seconds


async def _serve_dashboard_only(config: AppConfig, host: str | None, port: int | None) -> None:
    import uvicorn

    app = create_app(jsonl_path=config.dashboard.jsonl_file)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=host or config.dashboard.host,
            port=port or config.dashboard.port,
            log_level="warning",
        )
    )
    await server.serve()


async def _run_with_dashboard(config: AppConfig, duration: float, host: str | None, port: int | None) -> World:
    import uvicorn

    world = World(config)
    runner = SimulationRunner(world)

    app = create_app(
        world_provider=lambda: world,
        runner_provider=lambda: runner,
        jsonl_path=config.dashboard.jsonl_file,
    )
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=host or config.dashboard.host,
            port=port or config.dashboard.port,
            log_level="warning",
        )
    )

    run_task = asyncio.create_task(runner.run(duration))
    server_task = asyncio.create_task(server.serve())

    try:
        await run_task
    finally:
        server.should_exit = True
        await server_task

    return world


async def _run_headless(config: AppConfig, duration: float) -> World:
    world = World(config)
    runner = SimulationRunner(world)
    return await runner.run(duration)


def main() -> int:
    load_dotenv()
    args = _parse_args()

    os.chdir(Path(__file__).resolve().parents[2])

    config = _load_runtime_config(
        args.config,
        args.agents,
        args.model,
        args.llm_loop,
        args.loop_llm_cooldown,
        args.loop_forced_explore,
        args.loop_policy_seed,
        args.loop_prompt_template,
    )

    if args.dashboard_only:
        asyncio.run(_serve_dashboard_only(config, args.host, args.port))
        return 0

    duration = _effective_duration(config, args.duration)

    if args.dashboard:
        world = asyncio.run(_run_with_dashboard(config, duration, args.host, args.port))
    else:
        world = asyncio.run(_run_headless(config, duration))

    summary = world.get_state_summary(event_limit=20)
    print("=== AE3 complete ===")
    print(f"run_id: {summary.get('run_id')}")
    print(f"event_number: {summary.get('event_number')}")
    print(f"artifact_count: {summary.get('artifact_count')}")
    print(f"log_path: {summary.get('log_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
