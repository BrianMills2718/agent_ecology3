from __future__ import annotations

import asyncio

from agent_ecology3.config import AppConfig
from agent_ecology3.simulation import SimulationRunner
from agent_ecology3.world import World


def _make_config(tmp_path) -> AppConfig:
    cfg = AppConfig()
    cfg.principals.count = 1
    cfg.principals.id_prefix = "alpha_"
    cfg.principals.starting_scrip = 100
    cfg.principals.starting_llm_budget = 1.0
    cfg.principals.starting_disk_quota_bytes = 100_000

    cfg.simulation.default_duration_seconds = 0.8
    cfg.simulation.max_runtime_seconds = 10
    cfg.simulation.loop.min_delay_seconds = 0.05
    cfg.simulation.loop.max_delay_seconds = 0.25
    cfg.simulation.loop.max_consecutive_errors = 3
    cfg.simulation.loop.resource_check_interval_seconds = 0.05
    cfg.simulation.summary_interval_seconds = 0.5

    cfg.llm.enable_bootstrap_loop_llm = False
    cfg.dashboard.enabled = False

    cfg.logging.logs_dir = str(tmp_path / "logs")
    cfg.logging.recent_event_limit = 1000
    return cfg


def test_world_write_read_roundtrip(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    world = World(cfg, run_id="test_roundtrip")

    write_result = world.execute_action_data(
        "alpha_1",
        {
            "action_type": "write_artifact",
            "artifact_id": "alpha_1_note",
            "artifact_type": "note",
            "content": "hello world",
            "executable": False,
        },
    )
    assert write_result.success, write_result.message

    read_result = world.execute_action_data(
        "alpha_1",
        {
            "action_type": "read_artifact",
            "artifact_id": "alpha_1_note",
        },
    )
    assert read_result.success, read_result.message
    assert read_result.data is not None
    artifact = read_result.data.get("artifact", {})
    assert artifact.get("content") == "hello world"


def test_runner_executes_bootstrap_loop(tmp_path) -> None:
    cfg = _make_config(tmp_path)
    world = World(cfg, run_id="test_runner")
    runner = SimulationRunner(world)

    asyncio.run(runner.run(duration=1.0))

    assert world.event_number > 0
    events = world.logger.read_recent(500)
    event_types = {e.get("event_type") for e in events}
    assert "simulation_started" in event_types
    assert "simulation_stopped" in event_types
    assert "invoke_success" in event_types or "invoke_failure" in event_types
