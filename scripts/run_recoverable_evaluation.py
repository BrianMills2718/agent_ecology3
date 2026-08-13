#!/usr/bin/env python3
"""Operate the bounded recoverable Luna dashboard PoC from a fresh process."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Literal, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_ecology3.analysis.luna_recovery_gate import (
    REVIEWED_LLM_CLIENT_REVISION,
    _git_source_status,
    build_provider_free_preflight,
)
from agent_ecology3.config import AppConfig, load_config
from agent_ecology3.dashboard import create_app
from agent_ecology3.simulation import (
    RecoverableLoopWorld,
    RecoveryCoordinator,
    RecoveryScarcityBoundary,
    RecoveryTerminalError,
    SimulationRunner,
    build_recoverable_world,
)
from agent_ecology3.world.luna_actions import (
    LUNA_MODEL,
    shared_client_source_status,
)

ACKNOWLEDGEMENT = "plan10/luna-medium/dashboard-poc/v1"
SCARCITY_ACKNOWLEDGEMENT = "plan11/luna-medium/scarcity-midpoint/v1"
SCARCITY_STARTING_BUDGET = 0.033192
SCARCITY_TARGET_ATTEMPTS = 16
SCARCITY_CONTROL_ACKNOWLEDGEMENT = "plan11/luna-medium/scarcity-control/v1"
SCARCITY_CONTROL_STARTING_BUDGET = 0.066384
SCARCITY_CONTROL_TARGET_ATTEMPTS = 8
EVAL12_ACKNOWLEDGEMENTS = {
    "prescribed": "eval12/luna-medium/prescribed/pair-01/v1",
    "minimal": "eval12/luna-medium/minimal/pair-01/v1",
}
EVAL12_STARTING_BUDGET = 0.033192
EVAL12_TARGET_ATTEMPTS = 16
EVAL12_PRINCIPAL_COUNT = 2
EVAL12_POLICY_SEED = 24120
EVAL14_ACKNOWLEDGEMENTS = {
    "prescribed": "eval14/luna-medium/prescribed/pair-01/v1",
    "minimal": "eval14/luna-medium/minimal/pair-01/v1",
}
EVAL14_STARTING_BUDGET = 0.033192
EVAL14_TARGET_ATTEMPTS = 15
EVAL14_PRINCIPAL_COUNT = 2
EVAL14_POLICY_SEED = 24140
EVAL15_ACKNOWLEDGEMENTS = {
    "prescribed": "eval15/luna-medium/prescribed/pair-01/v1",
    "minimal": "eval15/luna-medium/minimal/pair-01/v1",
}
EVAL15_STARTING_BUDGET = 0.033192
EVAL15_TARGET_ATTEMPTS = 14
EVAL15_PRINCIPAL_COUNT = 2
EVAL15_POLICY_SEED = 24150
PLAN19_ACKNOWLEDGEMENT = "plan19/luna-medium/live-economic-mvp/v1"
PLAN19_STARTING_BUDGET = 0.033192
PLAN19_TARGET_ATTEMPTS = 14
PLAN19_PRINCIPAL_COUNT = 2
PLAN19_POLICY_SEED = 24190
DEFAULT_RUN_ID = "plan10_luna_dashboard_poc_v1"


def _default_data_dir() -> Path:
    state_root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return state_root / "agent_ecology3" / "plan10_luna_dashboard_poc_v1"


def _dashboard_launch_profile() -> dict[str, Any]:
    return {
        "model": LUNA_MODEL,
        "reasoning_effort": "medium",
        "cognition_mode": "minimal",
        "principal_count": PLAN19_PRINCIPAL_COUNT,
        "target_attempts": PLAN19_TARGET_ATTEMPTS,
        "starting_llm_budget_per_principal": PLAN19_STARTING_BUDGET,
        "billing": "subscription included",
        "starts_paused": True,
    }


def _launch_dashboard_run(args: argparse.Namespace) -> dict[str, Any]:
    """Launch the frozen MVP profile through the canonical paused worker path."""
    timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    run_id = f"plan21_luna_dashboard_{timestamp}"
    state_root = Path(
        os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")
    )
    launch_args = argparse.Namespace(
        acknowledgement=PLAN19_ACKNOWLEDGEMENT,
        data_dir=str(state_root / "agent_ecology3" / run_id),
        config=args.config,
        run_id=run_id,
        target_attempts=PLAN19_TARGET_ATTEMPTS,
        starting_llm_budget=PLAN19_STARTING_BUDGET,
        principal_count=PLAN19_PRINCIPAL_COUNT,
        cognition_mode="minimal",
        policy_seed=PLAN19_POLICY_SEED,
        host=args.host,
        port=args.launch_port,
    )
    return {
        **_spawn(launch_args, start_running=False),
        "profile": _dashboard_launch_profile(),
    }


def _paths(data_dir: Path) -> dict[str, Path]:
    return {
        "checkpoint": data_dir / "checkpoint.json",
        "status": data_dir / "status.json",
        "worker_log": data_dir / "worker.log",
        "receipt": data_dir / "run_receipt.json",
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _configure(
    config_path: Path,
    data_dir: Path,
    *,
    starting_llm_budget: float | None = None,
    principal_count: int = 1,
    cognition_mode: str = "prescribed",
    policy_seed: int = 0,
    action_failure_policy: Literal[
        "recovery_fallback", "fail_closed_no_substitute"
    ] = "recovery_fallback",
    mint_enabled: bool = False,
    mint_auction_after_horizon: bool = False,
) -> AppConfig:
    config = load_config(config_path)
    config.principals.count = principal_count
    config.principals.starting_llm_budget = (
        max(1.0, float(config.principals.starting_llm_budget))
        if starting_llm_budget is None
        else float(starting_llm_budget)
    )
    config.mint.enabled = mint_enabled
    config.logging.logs_dir = str(data_dir / "logs")
    config.logging.recent_event_limit = 2000
    config.simulation.default_duration_seconds = 3600
    config.simulation.max_runtime_seconds = 7200
    if mint_auction_after_horizon:
        config.mint.first_auction_delay_seconds = (
            config.simulation.default_duration_seconds + 1.0
        )
        config.mint.scoring_max_budget = 0.0
    config.simulation.loop.min_delay_seconds = 3.0
    config.simulation.loop.max_delay_seconds = 3.0
    config.llm.default_model = LUNA_MODEL
    config.llm.allowed_models = [LUNA_MODEL]
    config.llm.num_retries = 0
    config.llm.agent_cwd = None
    config.llm.enable_bootstrap_loop_llm = True
    config.llm.loop_llm_cooldown_seconds = 0.0
    config.llm.loop_forced_explore_mode = "off"
    config.llm.loop_cognition_mode = cast(
        Literal["prescribed", "minimal"], cognition_mode
    )
    config.llm.loop_policy_seed = policy_seed
    config.llm.loop_action_failure_policy = action_failure_policy
    config.llm.decision_output_mode = "luna_structured_v1"
    config.llm.reasoning_effort = "medium"
    config.llm.codex_transport = "cli"
    config.llm.codex_sandbox_mode = "read-only"
    config.llm.codex_approval_policy = "never"
    config.llm.codex_isolate_home = True
    config.llm.structured_response_model = "LunaLoopDecisionV1"
    config.llm.expected_billing_mode = "subscription_included"
    return AppConfig.model_validate(config.model_dump())


def _preflight() -> dict[str, Any]:
    ae3_revision, ae3_clean, ae3_pushed = _git_source_status(REPO_ROOT)
    client_revision, client_clean = shared_client_source_status()
    if not ae3_revision or not ae3_clean or not ae3_pushed:
        raise RuntimeError("PoC requires a clean Agent Ecology 3 revision pushed to its upstream")
    if client_revision != REVIEWED_LLM_CLIENT_REVISION or not client_clean:
        raise RuntimeError("PoC requires the exact clean reviewed llm_client revision")
    import llm_client

    module_file = getattr(llm_client, "__file__", None)
    if not isinstance(module_file, str) or not module_file:
        raise RuntimeError("cannot resolve the imported llm_client source checkout")
    client_root_result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path(module_file).resolve().parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if client_root_result.returncode != 0 or not client_root_result.stdout.strip():
        raise RuntimeError("imported llm_client is not from a Git checkout")
    provider_free = build_provider_free_preflight(
        llm_client_repo=Path(client_root_result.stdout.strip())
    )
    if provider_free.status != "pass":
        raise RuntimeError(
            f"provider-free Luna preflight blocked: {provider_free.blocker_code}: "
            f"{provider_free.blocker_reason}"
        )
    return {
        "agent_ecology3_revision": ae3_revision,
        "agent_ecology3_source_clean": ae3_clean,
        "agent_ecology3_source_pushed": ae3_pushed,
        "llm_client_revision": client_revision,
        "llm_client_source_clean": client_clean,
    }


def _post_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"dashboard control failed: {exc}") from exc
    return payload if isinstance(payload, dict) else {"success": False, "error": "invalid response"}


def _validate_start_contract(args: argparse.Namespace) -> None:
    if args.acknowledgement == PLAN19_ACKNOWLEDGEMENT:
        if (
            args.target_attempts != PLAN19_TARGET_ATTEMPTS
            or args.principal_count != PLAN19_PRINCIPAL_COUNT
            or args.cognition_mode != "minimal"
            or args.policy_seed != PLAN19_POLICY_SEED
            or not math.isclose(
                float(args.starting_llm_budget or -1),
                PLAN19_STARTING_BUDGET,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise RuntimeError(
                "Plan 19 requires exactly 14 attempts, two principals, Minimal "
                "cognition, seed 24190, and starting_llm_budget=0.033192"
            )
        return
    expected_eval15_ack = EVAL15_ACKNOWLEDGEMENTS.get(
        getattr(args, "cognition_mode", None)
    )
    if args.acknowledgement == expected_eval15_ack:
        if (
            args.target_attempts != EVAL15_TARGET_ATTEMPTS
            or args.principal_count != EVAL15_PRINCIPAL_COUNT
            or args.policy_seed != EVAL15_POLICY_SEED
            or not math.isclose(
                float(args.starting_llm_budget or -1),
                EVAL15_STARTING_BUDGET,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise RuntimeError(
                "Evaluation 15 requires exactly 14 attempts, two principals, "
                "seed 24150, and starting_llm_budget=0.033192"
            )
        return
    expected_eval14_ack = EVAL14_ACKNOWLEDGEMENTS.get(
        getattr(args, "cognition_mode", None)
    )
    if args.acknowledgement == expected_eval14_ack:
        if (
            args.target_attempts != EVAL14_TARGET_ATTEMPTS
            or args.principal_count != EVAL14_PRINCIPAL_COUNT
            or args.policy_seed != EVAL14_POLICY_SEED
            or not math.isclose(
                float(args.starting_llm_budget or -1),
                EVAL14_STARTING_BUDGET,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise RuntimeError(
                "Evaluation 14 requires exactly 15 attempt records, two principals, "
                "seed 24140, and starting_llm_budget=0.033192"
            )
        return
    if args.acknowledgement == ACKNOWLEDGEMENT:
        if args.target_attempts != 2 or args.starting_llm_budget is not None:
            raise RuntimeError("Plan 10 is frozen to two attempts and its original budget")
        return
    if args.acknowledgement == SCARCITY_ACKNOWLEDGEMENT:
        if args.target_attempts != SCARCITY_TARGET_ATTEMPTS or not math.isclose(
            float(args.starting_llm_budget or -1),
            SCARCITY_STARTING_BUDGET,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise RuntimeError(
                "Plan 11 requires exactly 16 target attempts and starting_llm_budget=0.033192"
            )
        return
    if args.acknowledgement == SCARCITY_CONTROL_ACKNOWLEDGEMENT:
        if args.target_attempts != SCARCITY_CONTROL_TARGET_ATTEMPTS or not math.isclose(
            float(args.starting_llm_budget or -1),
            SCARCITY_CONTROL_STARTING_BUDGET,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise RuntimeError(
                "Plan 11 control requires exactly 8 target attempts and "
                "starting_llm_budget=0.066384"
            )
        return
    expected_eval12_ack = EVAL12_ACKNOWLEDGEMENTS.get(args.cognition_mode)
    if args.acknowledgement == expected_eval12_ack:
        if (
            args.target_attempts != EVAL12_TARGET_ATTEMPTS
            or args.principal_count != EVAL12_PRINCIPAL_COUNT
            or args.policy_seed != EVAL12_POLICY_SEED
            or not math.isclose(
                float(args.starting_llm_budget or -1),
                EVAL12_STARTING_BUDGET,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise RuntimeError(
                "Evaluation 12 requires exactly 16 attempts, two principals, "
                "seed 24120, and starting_llm_budget=0.033192"
            )
        return
    raise RuntimeError(
        "start requires an exact Plan 10, Plan 11, or Evaluation 12 acknowledgement, "
        "an exact Evaluation 14 or Evaluation 15 acknowledgement, or the exact "
        "Plan 19 MVP acknowledgement"
    )


def _seed_mvp_opportunities(world: RecoverableLoopWorld) -> list[str]:
    """Seed legal priced opportunities without selecting any agent action."""
    if world.principal_ids != ["alpha_1", "alpha_2"]:
        raise RuntimeError("Plan 19 scenario requires exactly alpha_1 and alpha_2")
    opportunities = (
        (
            "alpha_1_market_signal",
            "market_signal",
            "alpha_1",
            "A concise market signal: priced cross-agent knowledge can be purchased "
            "when its expected future value exceeds its scrip cost.",
        ),
        (
            "alpha_2_validation_guide",
            "validation_guide",
            "alpha_2",
            "A reusable validation guide: inspect provenance, affordability, and "
            "downstream usefulness before relying on an artifact.",
        ),
    )
    for artifact_id, artifact_type, owner, content in opportunities:
        world.artifacts.write(
            artifact_id,
            artifact_type,
            content,
            created_by=owner,
            owner=owner,
            read_price=2,
            access_contract_id="kernel_contract_freeware",
            metadata={
                "mvp_scenario_opportunity": True,
                "fixture_not_agent_action": True,
            },
        )
    return [item[0] for item in opportunities]


def _terminal_lifecycle(
    recovery: dict[str, Any],
) -> Literal["completed", "stopped", "invalid"]:
    """Classify terminal custody from durable progress, not a transient heartbeat."""
    if recovery.get("lifecycle_state") == "invalid":
        return "invalid"
    committed = int(recovery.get("committed_attempts", 0) or 0)
    target = int(recovery.get("target_attempts", 0) or 0)
    if target > 0 and committed >= target:
        return "completed"
    return "stopped"


def _spawn(args: argparse.Namespace, *, start_running: bool) -> dict[str, Any]:
    _validate_start_contract(args)
    data_dir = Path(args.data_dir).expanduser().resolve()
    paths = _paths(data_dir)
    existing = _read_json(paths["status"])
    if existing is not None and _pid_alive(existing.get("pid")):
        raise RuntimeError(f"worker already alive with pid {existing.get('pid')}")
    source = _preflight()
    data_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "serve",
        "--acknowledgement",
        args.acknowledgement,
        "--data-dir",
        str(data_dir),
        "--config",
        str(Path(args.config).resolve()),
        "--run-id",
        args.run_id,
        "--target-attempts",
        str(args.target_attempts),
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if args.starting_llm_budget is not None:
        command.extend(["--starting-llm-budget", str(args.starting_llm_budget)])
    command.extend(
        [
            "--principal-count",
            str(args.principal_count),
            "--cognition-mode",
            args.cognition_mode,
            "--policy-seed",
            str(args.policy_seed),
        ]
    )
    if start_running:
        command.append("--start-running")
    worker_env = os.environ.copy()
    worker_env["LLM_CLIENT_PROJECT"] = "agent_ecology3"
    with paths["worker_log"].open("a", encoding="utf-8") as output:
        process = subprocess.Popen(
            command,
            cwd=data_dir,
            env=worker_env,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    deadline = time.monotonic() + 10
    status: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        status = _read_json(paths["status"])
        if status is not None and status.get("pid") == process.pid:
            break
        if process.poll() is not None:
            raise RuntimeError(f"worker exited during launch; inspect {paths['worker_log']}")
        time.sleep(0.1)
    if status is None or status.get("pid") != process.pid:
        raise RuntimeError(f"worker did not publish status; inspect {paths['worker_log']}")
    return {
        "success": True,
        "pid": process.pid,
        "url": f"http://{args.host}:{args.port}/",
        "data_dir": str(data_dir),
        "source": source,
        "status": status,
    }


def _write_receipt(
    *,
    data_dir: Path,
    coordinator: RecoveryCoordinator,
    world: RecoverableLoopWorld,
    source: dict[str, Any],
    acknowledgement: str,
) -> None:
    checkpoint = _read_json(_paths(data_dir)["checkpoint"]) or {}
    raw_attempts = checkpoint.get("attempts")
    attempts: list[Any] = raw_attempts if isinstance(raw_attempts, list) else []
    shared_receipts: list[dict[str, Any]] = []
    try:
        from llm_client import get_llm_call_receipts

        for attempt in attempts:
            trace_id = attempt.get("trace_id") if isinstance(attempt, dict) else None
            if not isinstance(trace_id, str) or not trace_id:
                continue
            shared_receipts.extend(
                receipt.model_dump(mode="json")
                for receipt in get_llm_call_receipts(trace_id=trace_id)
            )
    except Exception as exc:  # noqa: BLE001 - retain a truthful evidence blocker
        shared_receipts = [{"receipt_error": f"{type(exc).__name__}: {exc}"}]
    payload = {
        "schema_version": "ae3_luna_recoverable_run_receipt.v1",
        "acknowledgement": acknowledgement,
        "model": LUNA_MODEL,
        "reasoning_effort": "medium",
        "transport": "cli",
        "mcp_servers": [],
        "retry_count": 0,
        "fallback_models": [],
        "source": source,
        "starting_llm_budget": world.config.principals.starting_llm_budget,
        "principal_count": world.config.principals.count,
        "cognition_mode": world.config.llm.loop_cognition_mode,
        "policy_seed": world.config.llm.loop_policy_seed,
        "local_action_failure_policy": world.config.llm.loop_action_failure_policy,
        "mvp_scenario_opportunities": [
            artifact.id
            for artifact in world.artifacts.artifacts.values()
            if artifact.metadata.get("mvp_scenario_opportunity") is True
        ],
        "mint": {
            "enabled": world.config.mint.enabled,
            "first_auction_delay_seconds": world.config.mint.first_auction_delay_seconds,
            "scoring_max_budget": world.config.mint.scoring_max_budget,
        },
        "recovery": coordinator.status(),
        "checkpoint": checkpoint,
        "shared_client_receipts": shared_receipts,
        "world_state": world.get_state_summary(event_limit=200),
    }
    path = _paths(data_dir)["receipt"]
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


async def _serve(args: argparse.Namespace) -> None:
    _validate_start_contract(args)
    import uvicorn

    data_dir = Path(args.data_dir).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    source = _preflight()
    is_fail_closed_evaluation = args.acknowledgement in {
        *EVAL14_ACKNOWLEDGEMENTS.values(),
        *EVAL15_ACKNOWLEDGEMENTS.values(),
        PLAN19_ACKNOWLEDGEMENT,
    }
    config = _configure(
        Path(args.config).resolve(),
        data_dir,
        starting_llm_budget=args.starting_llm_budget,
        principal_count=args.principal_count,
        cognition_mode=args.cognition_mode,
        policy_seed=args.policy_seed,
        action_failure_policy=(
            "fail_closed_no_substitute"
            if is_fail_closed_evaluation
            else "recovery_fallback"
        ),
        mint_enabled=is_fail_closed_evaluation,
        mint_auction_after_horizon=is_fail_closed_evaluation,
    )
    world, coordinator = build_recoverable_world(
        config,
        run_id=args.run_id,
        target_attempts=args.target_attempts,
        checkpoint_path=_paths(data_dir)["checkpoint"],
        status_path=_paths(data_dir)["status"],
    )
    if args.acknowledgement == PLAN19_ACKNOWLEDGEMENT:
        _seed_mvp_opportunities(world)
    runner = SimulationRunner(world)
    coordinator.publish_status(
        "running" if args.start_running else "paused",
        pid=os.getpid(),
    )
    server: uvicorn.Server | None = None

    def request_shutdown() -> None:
        if server is None:
            raise RuntimeError("server unavailable during shutdown")
        server.should_exit = True

    app = create_app(
        world_provider=lambda: world,
        runner_provider=lambda: runner,
        recovery_provider=coordinator.status,
        shutdown_provider=request_shutdown,
        jsonl_path=str(world.logger.output_path),
    )
    server = uvicorn.Server(
        uvicorn.Config(app, host=args.host, port=args.port, log_level="warning")
    )
    run_task = asyncio.create_task(
        runner.run(
            duration=float(config.simulation.default_duration_seconds),
            target_llm_attempts=args.target_attempts,
            start_paused=not args.start_running,
        )
    )
    receipt_written = False

    async def heartbeat() -> None:
        nonlocal receipt_written
        while not server.should_exit:
            if run_task.done():
                lifecycle = _terminal_lifecycle(coordinator.status())
                coordinator.publish_status(lifecycle, pid=os.getpid())
                if not receipt_written:
                    _write_receipt(
                        data_dir=data_dir,
                        coordinator=coordinator,
                        world=world,
                        source=source,
                        acknowledgement=args.acknowledgement,
                    )
                    receipt_written = True
            else:
                lifecycle = "paused" if runner.is_paused else "running"
                coordinator.publish_status(lifecycle, pid=os.getpid())
            await asyncio.sleep(1)

    heartbeat_task = asyncio.create_task(heartbeat())
    try:
        await server.serve()
    finally:
        runner.stop()
        await asyncio.gather(run_task, return_exceptions=True)
        heartbeat_task.cancel()
        await asyncio.gather(heartbeat_task, return_exceptions=True)
        final_lifecycle = _terminal_lifecycle(coordinator.status())
        coordinator.publish_status(final_lifecycle, pid=os.getpid())
        _write_receipt(
            data_dir=data_dir,
            coordinator=coordinator,
            world=world,
            source=source,
            acknowledgement=args.acknowledgement,
        )


def _validate_review_run(data_dir: Path) -> None:
    """Fail before serving when preserved custody cannot support read-only review."""
    receipt_path = data_dir / "run_receipt.json"
    receipt = _read_json(receipt_path)
    if receipt is None:
        raise RuntimeError(f"invalid completed-run receipt: {receipt_path}")
    world_state = receipt.get("world_state")
    recovery = receipt.get("recovery")
    if not isinstance(world_state, dict) or not isinstance(recovery, dict):
        raise RuntimeError(f"completed-run receipt is missing run state: {receipt_path}")
    raw_log_path = world_state.get("log_path")
    if not isinstance(raw_log_path, str) or not raw_log_path:
        raise RuntimeError(f"completed-run receipt has no event log: {receipt_path}")
    if not Path(raw_log_path).is_file():
        raise RuntimeError(
            f"completed-run event log does not exist: {raw_log_path}"
        )


def _discover_review_runs(review_root: Path) -> dict[str, Path]:
    """Discover one direct run or immediate receipt-bearing run directories."""
    if (review_root / "run_receipt.json").is_file():
        _validate_review_run(review_root)
        return {review_root.name: review_root}

    candidates = sorted(
        (
            child
            for child in review_root.iterdir()
            if child.is_dir() and (child / "run_receipt.json").is_file()
        ),
        key=lambda path: (
            {"prescribed": 0, "minimal": 1}.get(path.name, 2),
            path.name,
        ),
    ) if review_root.is_dir() else []
    if not candidates:
        raise RuntimeError(
            "completed-run review requires a run_receipt.json in the selected "
            f"directory or one of its immediate children: {review_root}"
        )
    for data_dir in candidates:
        _validate_review_run(data_dir)
    return {data_dir.name: data_dir for data_dir in candidates}


async def _review(args: argparse.Namespace) -> None:
    """Serve preserved runs read-only without reconstructing a world."""
    import uvicorn

    review_root = Path(args.data_dir).expanduser().resolve()
    review_runs = _discover_review_runs(review_root)
    app = create_app(
        review_runs=review_runs,
        launch_profile=_dashboard_launch_profile(),
        launch_provider=lambda: _launch_dashboard_run(args),
    )
    server = uvicorn.Server(
        uvicorn.Config(app, host=args.host, port=args.port, log_level="warning")
    )
    await server.serve()


def _status(args: argparse.Namespace) -> dict[str, Any]:
    data_dir = Path(args.data_dir).expanduser().resolve()
    status = _read_json(_paths(data_dir)["status"])
    if status is None:
        return {"success": False, "worker_alive": False, "error": "no durable status", "data_dir": str(data_dir)}
    status["success"] = True
    status["worker_alive"] = _pid_alive(status.get("pid"))
    status["data_dir"] = str(data_dir)
    status["worker_log"] = str(_paths(data_dir)["worker_log"])
    status["receipt"] = str(_paths(data_dir)["receipt"])
    return status


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "start",
            "serve",
            "review",
            "status",
            "resume",
            "pause",
            "stop",
            "shutdown",
        ),
    )
    parser.add_argument("--acknowledgement", default="")
    parser.add_argument("--data-dir", default=str(_default_data_dir()))
    parser.add_argument("--config", default=str(REPO_ROOT / "config" / "config.yaml"))
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--target-attempts", type=int, default=2)
    parser.add_argument("--starting-llm-budget", type=float)
    parser.add_argument("--principal-count", type=int, default=1)
    parser.add_argument("--cognition-mode", choices=("prescribed", "minimal"), default="prescribed")
    parser.add_argument("--policy-seed", type=int, default=0)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--launch-port", type=int, default=9021)
    parser.add_argument("--start-running", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "review":
        asyncio.run(_review(args))
        return 0
    if args.command == "serve":
        try:
            asyncio.run(_serve(args))
        except RecoveryScarcityBoundary as exc:
            print(json.dumps({"success": True, "terminal": "scarcity_binding", "reason": str(exc)}))
            return 0
        except RecoveryTerminalError as exc:
            print(json.dumps({"success": False, "terminal": "invalid", "error": str(exc)}))
            return 2
        return 0
    if args.command == "start":
        payload = _spawn(args, start_running=False)
    elif args.command == "status":
        payload = _status(args)
    elif args.command in {"resume", "pause", "stop"}:
        status = _status(args)
        if not status.get("worker_alive"):
            if args.command != "resume":
                payload = {**status, "success": False, "error": "worker is not alive"}
            else:
                payload = _spawn(args, start_running=True)
        else:
            payload = _post_json(f"http://{args.host}:{args.port}/control/{args.command}")
    else:
        status = _status(args)
        pid = status.get("pid")
        if not status.get("worker_alive") or not isinstance(pid, int):
            payload = {**status, "success": False, "error": "worker is not alive"}
        else:
            payload = _post_json(f"http://{args.host}:{args.port}/control/shutdown")
            payload["shutdown_pid"] = pid
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if payload.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
