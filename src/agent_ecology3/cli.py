"""Agent Ecology 3 command-line entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

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
    parser.add_argument("--dashboard", action="store_true", help="Run simulation with dashboard server")
    parser.add_argument("--dashboard-only", action="store_true", help="Run dashboard only (read existing JSONL logs)")
    parser.add_argument("--host", default=None, help="Dashboard host override")
    parser.add_argument("--port", type=int, default=None, help="Dashboard port override")
    return parser.parse_args()


def _load_runtime_config(path: str, agents_override: int | None) -> AppConfig:
    config = load_config(path)
    if agents_override is not None:
        if agents_override <= 0:
            raise ValueError("--agents must be > 0")
        config.principals.count = agents_override
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

    config = _load_runtime_config(args.config, args.agents)

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
