"""Frozen Evaluation 07 behavioral comparison runner and reproducer."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import shutil
import subprocess
import sys
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from ..config import AppConfig, load_config
from ..simulation import SimulationRunner
from ..world import World
from .emergence_report import summarize_events
from .provider_qualification import (
    _git_revision_and_cleanliness,
    _json_safe,
    _open_call_evidence,
    _run_public_readback_control_isolated,
    _sha256,
    _sha256_json,
    _verify_shared_custody_schema,
    classify_attempt,
)

EVALUATION_ID = 7
CONFIG_PATH = "config/config.behavioral_comparison_07.yaml"
CASES_PATH = "config/evaluations/07_behavioral_cases.json"
PREREGISTRATION_PATH = "docs/evaluations/07_behavioral_comparison.md"
DEFAULT_OUTPUT = "docs/evaluations/evidence/07_behavioral_comparison"
EXECUTION_DEADLINE = datetime(2026, 8, 19, 3, 33, 25, tzinfo=UTC)
MAX_ACTUAL_COST_USD = 1.68
PREREGISTRATION_RESULTS_MARKER = "\n## Results\n"
FROZEN_PREREGISTRATION_PREFIX_SHA256 = (
    "5e8234c853d081a66821f56f2b46f8993eae1187de38fd4d342b1225e2fa81ce"
)

FROZEN_INPUT_SHA256: dict[str, str] = {
    CONFIG_PATH: "285619a6b0e7c03dc284c68dc29a7527e616940aca6fc376b6b0d063e1f7ea38",
    CASES_PATH: "f6b85149b7c37d38c64d266243776f3cc60a245ee76edbf665a18da440e67f09",
    "config/prompts/loop_prompt_variant.txt": (
        "1c0219c4dc5dcf2aa0fb64b756546a4fa583c4e40a9f99108c7921a4b7fbc4b2"
    ),
    "config/prompts/loop_prompt_minimal.txt": (
        "c1029d2fda78e6309de66d229c9a872bf17a23f11465f94106aed7a88792f96a"
    ),
    PREREGISTRATION_PATH: "22b45f5aa776e13ce698c0270de04b992572f796cfec65ac27703393e2e4db61",
    "docs/evaluations/06_public_readback_qualification_signoff.md": (
        "eabb724e732bfa2b946ccd538d9801241302a747f2861c9b4496b5be576c73b2"
    ),
    "docs/evaluations/evidence/06_public_readback_qualification/SHA256SUMS": (
        "f1e3015781d8941fdfb9545b15d217811d32ad49ca70979fc3db26403d090e2b"
    ),
    "src/agent_ecology3/config.py": (
        "4cae1f7e38aa74aa028dccf432ff1a5aa2e95f71e583a9a32eaa4fb732e415e3"
    ),
    "src/agent_ecology3/world/world.py": (
        "a088fec29ee109c7458a1dfb1c9ef785611aab81f86fe24dbfec9f23a702ee97"
    ),
    "src/agent_ecology3/world/action_executor.py": (
        "685806400177df569b1e31d49cc3c8c855e2c1c7d73f7e056c4f986eedba2d39"
    ),
    "src/agent_ecology3/world/actions.py": (
        "05fea2088501b361060b1555b7bc8c60a1447406811ea138c0ab747ec2771fba"
    ),
    "src/agent_ecology3/world/artifacts.py": (
        "a45def77fe8a134d57f54a77ef573593e666de29b4b90818e05c4656ea46d794"
    ),
    "src/agent_ecology3/world/ledger.py": (
        "3b5bf7dcc7075264842c52686bb2f56627f7ff93887488628b7ba11379f425a5"
    ),
    "src/agent_ecology3/world/contracts.py": (
        "2162d62b6732d22e859654bf664355d739e0f56a076501cd4dcec4fa508790ca"
    ),
    "src/agent_ecology3/world/queries.py": (
        "fc12300543fa53820003bc941c1512de61547c7579e3dc4c89e3c4aa6231f17e"
    ),
    "src/agent_ecology3/world/mint.py": (
        "9627359a19fcec5ec3016988199b95999457e85a47dfad1b2dabd4ecbb1ac17f"
    ),
    "src/agent_ecology3/world/executor.py": (
        "ec07e396f91d8e69c1b7d8aede438427d0baf00556b987c6f64d6ac2ad5fe0a6"
    ),
    "src/agent_ecology3/analysis/emergence_report.py": (
        "a29f7db96d31d7a65d94eae02aaa7c75df665d346666623ddcd05992797e2973"
    ),
    "src/agent_ecology3/analysis/provider_qualification.py": (
        "daaa900438d7f3cc10b6b286f397c2fb98159d4c09447ecb648fc300807a1da4"
    ),
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _frozen_input_matches(relative: str, path: Path, expected: str) -> bool:
    digest = _sha256(path)
    if digest == expected:
        return True
    if relative != PREREGISTRATION_PATH:
        return False
    current = path.read_text(encoding="utf-8")
    prefix, marker, _results = current.partition(PREREGISTRATION_RESULTS_MARKER)
    prefix_digest = hashlib.sha256(prefix.encode("utf-8")).hexdigest()
    return bool(marker) and prefix_digest == FROZEN_PREREGISTRATION_PREFIX_SHA256


def _regular_files(root: Path) -> set[str]:
    return {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    }


def write_manifest(output: Path) -> None:
    lines = [
        f"{_sha256(output / relative)}  {relative}"
        for relative in sorted(_regular_files(output))
    ]
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_manifest(output: Path) -> dict[str, Any]:
    manifest_path = output / "SHA256SUMS"
    if not manifest_path.is_file():
        raise RuntimeError("evidence manifest is missing")
    observed_paths: set[str] = set()
    errors: list[str] = []
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            expected, relative = raw.split("  ", 1)
        except ValueError:
            errors.append(f"malformed manifest row: {raw}")
            continue
        observed_paths.add(relative)
        path = output / relative
        if not path.is_file():
            errors.append(f"missing manifest file: {relative}")
        elif _sha256(path) != expected:
            errors.append(f"manifest hash mismatch: {relative}")
    actual_paths = _regular_files(output)
    if actual_paths != observed_paths:
        errors.append(
            "manifest file set mismatch: "
            f"missing={sorted(actual_paths - observed_paths)} "
            f"extra={sorted(observed_paths - actual_paths)}"
        )
    if errors:
        raise RuntimeError("evidence manifest verification failed: " + "; ".join(errors))
    return {"passed": True, "files": len(observed_paths)}


def _load_cases(repo: Path) -> dict[str, Any]:
    value = _read_json(repo / CASES_PATH)
    if not isinstance(value, dict):
        raise TypeError("Evaluation 07 cases must be an object")
    return value


def _schedule_receipt(repo: Path, cases: dict[str, Any]) -> dict[str, Any]:
    rows = cases.get("pair_schedule")
    if not isinstance(rows, list):
        raise TypeError("Evaluation 07 pair schedule is missing")
    primary = [row for row in rows if isinstance(row, dict) and row.get("role") == "primary"]
    reserve = [row for row in rows if isinstance(row, dict) and row.get("role") == "reserve"]
    seeds = [int(row["seed"]) for row in rows if isinstance(row, dict)]
    orders = Counter(str(row.get("first_condition")) for row in rows if isinstance(row, dict))
    execution = cases.get("execution")
    if not isinstance(execution, dict):
        raise TypeError("Evaluation 07 execution contract is missing")
    attempts_per_run = int(execution.get("provider_attempts_per_run", -1))
    maximum_attempts = len(rows) * 2 * attempts_per_run
    maximum_cost = len(rows) * 2 * 0.06
    leakage: list[dict[str, Any]] = []
    receipt: dict[str, Any] = {
        "primary_pairs": len(primary),
        "reserve_pairs": len(reserve),
        "unique_seeds": len(seeds) == len(set(seeds)),
        "balanced_first_condition": orders == {"prescribed": 7, "minimal": 7},
        "maximum_provider_attempts": maximum_attempts,
        "maximum_actual_cost_usd": round(maximum_cost, 2),
        "leakage": leakage,
    }
    base_revision = str(cases.get("base_revision") or "")
    for seed in seeds:
        completed = subprocess.run(
            [
                "git",
                "grep",
                "-n",
                "--fixed-strings",
                str(seed),
                base_revision,
                "--",
                "docs",
                "config",
                "src",
                "tests",
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            leakage.append({"seed": seed, "matches": completed.stdout.splitlines()})
        elif completed.returncode not in {0, 1}:
            raise RuntimeError(f"seed leakage check failed for {seed}: {completed.stderr}")
    checks = [
        len(primary) == 12,
        len(reserve) == 2,
        receipt["unique_seeds"],
        receipt["balanced_first_condition"],
        maximum_attempts == int(execution.get("maximum_provider_attempts", -1)) == 448,
        math.isclose(maximum_cost, float(execution.get("maximum_actual_cost_usd", -1.0))),
        not leakage,
    ]
    if not all(checks):
        raise RuntimeError(f"frozen Evaluation 07 schedule invariant failed: {receipt}")
    return receipt


def verify_frozen_inputs(
    repo: Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    repo = repo.resolve()
    observed: dict[str, str] = {}
    for relative, expected in FROZEN_INPUT_SHA256.items():
        path = repo / relative
        digest = _sha256(path)
        observed[relative] = digest
        if not _frozen_input_matches(relative, path, expected):
            raise RuntimeError(
                f"frozen Evaluation 07 input mismatch for {relative}: "
                f"expected {expected}, observed {digest}"
            )
    check_time = now or datetime.now(UTC)
    if check_time.tzinfo is None:
        check_time = check_time.replace(tzinfo=UTC)
    if check_time > EXECUTION_DEADLINE:
        raise RuntimeError(
            "Evaluation 07 execution window expired; use a new-number qualification"
        )
    cases = _load_cases(repo)
    config = load_config(repo / CONFIG_PATH)
    if (
        config.llm.default_model != "minimax/minimax-m3"
        or config.llm.num_retries != 0
        or config.llm.max_output_tokens != 4096
        or not math.isclose(config.llm.provider_max_budget_usd, 0.06)
        or config.llm.loop_forced_explore_mode != "off"
        or config.principals.count != 4
        or config.principals.starting_scrip != 2
        or config.mint.first_auction_delay_seconds
        <= config.simulation.max_runtime_seconds
    ):
        raise RuntimeError("frozen Evaluation 07 config contract failed")
    return {
        "passed": True,
        "checked_at": check_time.astimezone(UTC).isoformat(),
        "execution_deadline": EXECUTION_DEADLINE.isoformat(),
        "frozen_input_sha256": observed,
        "schedule": _schedule_receipt(repo, cases),
    }


def _metric_control_events(*, origin: str, buyer: str, price: float) -> list[dict[str, Any]]:
    artifact_id = "alpha_1_control_artifact"
    return [
        {
            "timestamp": "2026-08-12T00:00:00+00:00",
            "event_type": "artifact_written",
            "principal_id": "alpha_1",
            "owner": "alpha_1",
            "artifact_id": artifact_id,
            "artifact_type": "note",
        },
        {
            "timestamp": "2026-08-12T00:00:01+00:00",
            "event_type": "loop_decision",
            "principal_id": "alpha_1",
            "decision_action": "write_artifact",
            "decision": {"action_type": "write_artifact", "artifact_id": artifact_id},
            "decision_origin": origin,
            "llm_attempted": origin == "llm_valid",
            "llm_success": origin == "llm_valid",
            "fallback_used": origin != "llm_valid",
            "forced_explore": False,
            "result_success": True,
        },
        {
            "timestamp": "2026-08-12T00:00:02+00:00",
            "event_type": "artifact_read",
            "principal_id": buyer,
            "artifact_id": artifact_id,
            "read_price_paid": price,
            "recipient": "alpha_1",
        },
    ]


def _summarize_synthetic(path: Path, events: list[dict[str, Any]]) -> dict[str, Any]:
    path.write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )
    return summarize_events(path)


def _run_metric_controls(temp: Path) -> dict[str, Any]:
    positive = _summarize_synthetic(
        temp / "positive.jsonl",
        _metric_control_events(origin="llm_valid", buyer="alpha_2", price=2.0),
    )
    fallback = _summarize_synthetic(
        temp / "fallback.jsonl",
        _metric_control_events(
            origin="llm_invalid_fallback", buyer="alpha_2", price=2.0
        ),
    )
    self_paid = _summarize_synthetic(
        temp / "self.jsonl",
        _metric_control_events(origin="llm_valid", buyer="alpha_1", price=2.0),
    )
    unpaid = _summarize_synthetic(
        temp / "unpaid.jsonl",
        _metric_control_events(origin="llm_valid", buyer="alpha_2", price=0.0),
    )
    negative_passed = all(
        float(summary.get("llm_valid_downstream_value", -1.0)) == 0.0
        for summary in (fallback, self_paid, unpaid)
    )
    return {
        "provider_calls": 0,
        "passed": bool(positive.get("llm_valid_downstream_value") == 2.0)
        and negative_passed,
        "positive": {
            "passed": float(positive.get("llm_valid_downstream_value", 0.0)) == 2.0,
            "llm_valid_downstream_value": positive.get("llm_valid_downstream_value"),
        },
        "negative": {
            "passed": negative_passed,
            "fallback_value": fallback.get("llm_valid_downstream_value"),
            "self_value": self_paid.get("llm_valid_downstream_value"),
            "unpaid_value": unpaid.get("llm_valid_downstream_value"),
        },
    }


def _run_llm_off_controls(repo: Path, temp: Path, cases: dict[str, Any]) -> dict[str, Any]:
    seeds = cases.get("llm_off_negative_control_seeds")
    if not isinstance(seeds, list) or len(seeds) != 3:
        raise RuntimeError("Eval07 requires exactly three LLM-off control seeds")
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        cfg = load_config(repo / CONFIG_PATH)
        cfg.llm.enable_bootstrap_loop_llm = False
        cfg.llm.loop_policy_seed = int(seed)
        cfg.simulation.max_runtime_seconds = 2.0
        cfg.logging.logs_dir = str(temp / "llm_off" / str(seed))
        world = World(cfg, run_id=f"llm_off_{seed}")
        asyncio.run(SimulationRunner(world).run(duration=0.05))
        summary = summarize_events(Path(world.logger.output_path))
        attempt_events = sum(
            1
            for event in world.logger.read_recent(2000)
            if event.get("event_type") in {"llm_syscall", "llm_syscall_error"}
        )
        rows.append(
            {
                "seed": int(seed),
                "provider_calls": attempt_events,
                "llm_valid_decisions": int(summary.get("llm_valid_decision_total", 0)),
                "llm_valid_downstream_value": float(
                    summary.get("llm_valid_downstream_value", 0.0)
                ),
            }
        )
    passed = all(
        row["provider_calls"] == 0
        and row["llm_valid_decisions"] == 0
        and row["llm_valid_downstream_value"] == 0.0
        for row in rows
    )
    return {
        "passed": passed,
        "runs": len(rows),
        "provider_calls": sum(int(row["provider_calls"]) for row in rows),
        "records": rows,
    }


def _synthetic_attempt_record() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    trace_id = "ae3/eval07/corruption/control"
    action = {
        "action_type": "query_kernel",
        "query_type": "resources",
        "params": {},
    }
    tool_call = {
        "id": "eval07-corruption-control",
        "type": "function",
        "function": {"name": "ae3_action", "arguments": json.dumps(action)},
    }
    messages = [{"role": "user", "content": "synthetic custody control"}]
    tools = [{"type": "function", "function": {"name": "ae3_action"}}]
    loop_decision = {
        "event_type": "loop_decision",
        "sequence": 3,
        "principal_id": "alpha_1",
        "llm_trace_id": trace_id,
        "llm_attempted": True,
        "llm_success": True,
        "decision_origin": "llm_valid",
        "decision": action,
        "decision_action": "query_kernel",
        "fallback_used": False,
        "forced_explore": False,
        "result_success": True,
        "result_error_code": None,
    }
    syscall_result = {
        "success": True,
        "trace_id": trace_id,
        "content": "",
        "tool_calls": [tool_call],
        "cache_hit": False,
    }
    receipt = {
        "trace_id": trace_id,
        "status": "succeeded",
        "finish_reason": "tool_calls",
        "retry_count": 0,
        "cache_hit": False,
        "cost_usd": 0.0,
    }
    call_record = {
        "trace_id": trace_id,
        "messages": messages,
        "response": "",
        "response_tool_calls": [tool_call],
        "call_snapshot": {"request": {"kwargs": {"tools": tools}}},
    }
    return (
        {
            "ordinal": 1,
            "condition": "control",
            "pair_id": "control",
            "principal_id": "alpha_1",
            "messages": messages,
            "messages_sha256": _sha256_json(messages),
            "tools": tools,
            "tools_sha256": _sha256_json(tools),
            "syscall_result": syscall_result,
            "receipts": [receipt],
            "call_record": call_record,
            "classification": classify_attempt(
                principal_id="alpha_1",
                syscall_result=syscall_result,
                receipt=receipt,
                call_record=call_record,
            ),
            "loop_decision": loop_decision,
            "cost_usd": 0.0,
        },
        [deepcopy(loop_decision)],
    )


def _snapshot_tools(call_record: dict[str, Any]) -> Any:
    snapshot = call_record.get("call_snapshot")
    if not isinstance(snapshot, dict):
        return None
    request = snapshot.get("request")
    if not isinstance(request, dict):
        return None
    kwargs = request.get("kwargs")
    if not isinstance(kwargs, dict):
        return None
    return kwargs.get("tools")


def verify_attempt_record(
    attempt: dict[str, Any],
    *,
    runtime_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    principal_id = str(attempt.get("principal_id") or "")
    syscall_result = attempt.get("syscall_result")
    receipts = attempt.get("receipts")
    call_record = attempt.get("call_record")
    if not isinstance(syscall_result, dict):
        errors.append("missing syscall result")
        syscall_result = {}
    if not isinstance(receipts, list) or len(receipts) != 1 or not isinstance(receipts[0], dict):
        errors.append("expected exactly one receipt")
        receipt: dict[str, Any] | None = None
    else:
        receipt = receipts[0]
    if not isinstance(call_record, dict):
        errors.append("missing public call record")
        call_record = {}
    trace_id = syscall_result.get("trace_id")
    if not isinstance(trace_id, str) or not trace_id:
        errors.append("missing trace id")
    else:
        if receipt is None or receipt.get("trace_id") != trace_id:
            errors.append("receipt trace id differs")
        if call_record.get("trace_id") != trace_id:
            errors.append("call record trace id differs")
    recomputed = classify_attempt(
        principal_id=principal_id,
        syscall_result=syscall_result,
        receipt=receipt,
        call_record=call_record,
    )
    if attempt.get("classification") != recomputed:
        errors.append("stored classification differs from recomputation")
    if call_record.get("messages") != attempt.get("messages"):
        errors.append("caller messages differ from public readback")
    if _snapshot_tools(call_record) != attempt.get("tools"):
        errors.append("caller tools differ from public readback snapshot")
    if call_record.get("response") != syscall_result.get("content"):
        errors.append("caller response differs from public readback")
    if call_record.get("response_tool_calls") != syscall_result.get("tool_calls"):
        errors.append("caller tool calls differ from public readback")
    if attempt.get("messages_sha256") != _sha256_json(attempt.get("messages")):
        errors.append("rendered messages hash differs")
    if attempt.get("tools_sha256") != _sha256_json(attempt.get("tools")):
        errors.append("rendered tools hash differs")
    if receipt is not None:
        if int(receipt.get("retry_count") or 0) != 0:
            errors.append("receipt records a retry")
        if bool(receipt.get("cache_hit")):
            errors.append("receipt records a cache hit")
    if bool(syscall_result.get("cache_hit")):
        errors.append("caller result records a cache hit")

    saved_loop = attempt.get("loop_decision")
    if not isinstance(saved_loop, dict):
        errors.append("missing normalized loop decision")
    if runtime_events is not None and isinstance(trace_id, str):
        matches = [
            event
            for event in runtime_events
            if event.get("event_type") == "loop_decision"
            and event.get("llm_trace_id") == trace_id
        ]
        if len(matches) != 1:
            errors.append("expected exactly one runtime loop decision")
        elif saved_loop != matches[0]:
            errors.append("saved normalized action differs from runtime loop decision")
    if isinstance(saved_loop, dict):
        if saved_loop.get("principal_id") != principal_id:
            errors.append("loop decision principal differs")
        if saved_loop.get("llm_trace_id") != trace_id:
            errors.append("loop decision trace differs")
    return {
        "passed": not errors,
        "errors": errors,
        "terminal_class": recomputed.get("terminal_class"),
    }


def _run_corruption_control() -> dict[str, Any]:
    attempt, runtime_events = _synthetic_attempt_record()
    positive = verify_attempt_record(attempt, runtime_events=runtime_events)
    corruptions: dict[str, dict[str, Any]] = {}

    trace = deepcopy(attempt)
    trace["syscall_result"]["trace_id"] = "ae3/eval07/corruption/changed"
    corruptions["trace"] = verify_attempt_record(trace, runtime_events=runtime_events)

    tool = deepcopy(attempt)
    tool["syscall_result"]["tool_calls"][0]["function"]["arguments"] = (
        '{"action_type":"transfer","recipient_id":"alpha_2","amount":1}'
    )
    corruptions["raw_tool"] = verify_attempt_record(tool, runtime_events=runtime_events)

    normalized = deepcopy(attempt)
    normalized["loop_decision"]["decision"]["action_type"] = "transfer"
    corruptions["normalized_action"] = verify_attempt_record(
        normalized, runtime_events=runtime_events
    )

    origin = deepcopy(attempt)
    origin["loop_decision"]["decision_origin"] = "llm_invalid_fallback"
    corruptions["decision_origin"] = verify_attempt_record(
        origin, runtime_events=runtime_events
    )
    return {
        "provider_calls": 0,
        "passed": positive["passed"] is True
        and all(result["passed"] is False for result in corruptions.values()),
        "positive": positive,
        "corruptions": corruptions,
    }


def run_preflight(
    repo: Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    repo = repo.resolve()
    frozen = verify_frozen_inputs(repo, now=now)
    eval06_manifest = verify_manifest(
        repo / "docs/evaluations/evidence/06_public_readback_qualification"
    )
    _verify_shared_custody_schema()
    public = _run_public_readback_control_isolated(repo)
    cases = _load_cases(repo)
    with TemporaryDirectory(prefix="ae3-eval07-preflight-") as temp_dir:
        temp = Path(temp_dir)
        metric = _run_metric_controls(temp)
        llm_off = _run_llm_off_controls(repo, temp, cases)
    corruption = _run_corruption_control()
    passed = (
        bool(public.get("passed"))
        and bool(metric["positive"]["passed"])
        and bool(metric["negative"]["passed"])
        and bool(llm_off["passed"])
        and bool(corruption["passed"])
        and bool(eval06_manifest["passed"])
    )
    return {
        "schema_version": "ae3_eval07_preflight_v1",
        "passed": passed,
        "provider_calls": 0,
        "frozen_inputs": frozen,
        "eval06_manifest": eval06_manifest,
        "public_readback": public,
        "metric_controls": metric,
        "llm_off": llm_off,
        "corruption": corruption,
    }


def evaluate_run(
    *,
    condition: str,
    pair_id: str,
    attempts: list[dict[str, Any]],
    summary: dict[str, Any],
    scarcity_receipts: list[dict[str, Any]],
    auxiliary_provider_calls: int,
    runtime_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    classes = Counter(
        str(attempt.get("classification", {}).get("terminal_class") or "missing")
        for attempt in attempts
    )
    principals = Counter(str(attempt.get("principal_id") or "") for attempt in attempts)
    failed_checks: list[str] = []
    if len(attempts) != 16:
        failed_checks.append("exact_attempts")
    if (
        set(principals) != {"alpha_1", "alpha_2", "alpha_3", "alpha_4"}
        or any(count < 3 or count > 5 for count in principals.values())
    ):
        failed_checks.append("attempt_distribution")
    if int(summary.get("llm_valid_decision_total", 0)) < 15:
        failed_checks.append("minimum_llm_valid_decisions")
    forbidden_classes = {
        "provider_error",
        "provider_timeout",
        "output_truncation",
        "trace_failure",
        "custody_failure",
    }
    if any(classes[name] for name in forbidden_classes):
        failed_checks.append("terminal_classes")
    if float(summary.get("forced_explore_rate", 0.0)) != 0.0 or any(
        bool(attempt.get("loop_decision", {}).get("forced_explore"))
        for attempt in attempts
    ):
        failed_checks.append("forced_explore")
    if auxiliary_provider_calls != 0:
        failed_checks.append("auxiliary_provider_calls")
    if any(
        int((attempt.get("receipts") or [{}])[0].get("retry_count") or 0) != 0
        or bool((attempt.get("receipts") or [{}])[0].get("cache_hit"))
        or bool(attempt.get("syscall_result", {}).get("cache_hit"))
        for attempt in attempts
    ):
        failed_checks.append("retry_or_cache")
    if any(attempt.get("verification", {}).get("passed") is False for attempt in attempts):
        failed_checks.append("attempt_custody")
    if runtime_events is not None:
        settled = [
            event
            for event in runtime_events
            if event.get("event_type") in {"llm_syscall", "llm_syscall_error"}
        ]
        attempt_traces = [
            str(attempt.get("syscall_result", {}).get("trace_id") or "")
            for attempt in attempts
        ]
        settled_traces = [str(event.get("trace_id") or "") for event in settled]
        if (
            len(settled) != 16
            or len(set(attempt_traces)) != len(attempt_traces)
            or Counter(settled_traces) != Counter(attempt_traces)
        ):
            failed_checks.append("runtime_attempt_events")
        linked_loop_sequences = [
            int(event.get("sequence") or 0)
            for event in runtime_events
            if event.get("event_type") == "loop_decision"
            and event.get("llm_trace_id") in set(attempt_traces)
        ]
        if linked_loop_sequences:
            final_linked_sequence = max(linked_loop_sequences)
            if any(
                event.get("event_type") == "loop_decision"
                and int(event.get("sequence") or 0) > final_linked_sequence
                for event in runtime_events
            ):
                failed_checks.append("post_target_loop_decision")
        else:
            failed_checks.append("runtime_loop_decisions")
    actual_cost = sum(float(attempt.get("cost_usd") or 0.0) for attempt in attempts)
    return {
        "condition": condition,
        "pair_id": pair_id,
        "valid": not failed_checks,
        "failed_checks": failed_checks,
        "attempts": len(attempts),
        "attempt_distribution": dict(sorted(principals.items())),
        "terminal_classes": dict(sorted(classes.items())),
        "llm_valid_decisions": int(summary.get("llm_valid_decision_total", 0)),
        "forced_explore_rate": float(summary.get("forced_explore_rate", 0.0)),
        "scarcity_binding": bool(scarcity_receipts),
        "scarcity_receipts": scarcity_receipts,
        "primary_positive": float(summary.get("llm_valid_downstream_value", 0.0)) > 0.0,
        "llm_valid_downstream_value": float(
            summary.get("llm_valid_downstream_value", 0.0)
        ),
        "actual_cost_usd": round(actual_cost, 8),
        "auxiliary_provider_calls": int(auxiliary_provider_calls),
        "summary": summary,
    }


def _wilson_interval(successes: int, total: int) -> list[float]:
    if total <= 0:
        return [0.0, 0.0]
    z = 1.959963984540054
    p = successes / total
    denominator = 1.0 + (z * z / total)
    center = (p + z * z / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt((p * (1 - p) / total) + z * z / (4 * total * total))
        / denominator
    )
    return [round(max(0.0, center - margin), 8), round(min(1.0, center + margin), 8)]


def _one_sided_exact(discordant_high: int, discordant_total: int) -> float:
    if discordant_total <= 0:
        return 1.0
    tail = sum(
        math.comb(discordant_total, value)
        for value in range(discordant_high, discordant_total + 1)
    )
    return float(tail / (2**discordant_total))


def compute_readout(
    pairs: list[dict[str, Any]],
    *,
    controls_passed: bool = True,
) -> dict[str, Any]:
    valid = [
        pair
        for pair in pairs
        if pair.get("valid") is True and pair.get("included", True) is True
    ][:12]
    prescribed = sum(
        bool(pair.get("runs", {}).get("prescribed", {}).get("primary_positive"))
        for pair in valid
    )
    minimal = sum(
        bool(pair.get("runs", {}).get("minimal", {}).get("primary_positive"))
        for pair in valid
    )
    b = sum(
        bool(pair["runs"]["prescribed"]["primary_positive"])
        and not bool(pair["runs"]["minimal"]["primary_positive"])
        for pair in valid
    )
    c = sum(
        bool(pair["runs"]["minimal"]["primary_positive"])
        and not bool(pair["runs"]["prescribed"]["primary_positive"])
        for pair in valid
    )
    high_discordance = max(b, c)
    exact_p = _one_sided_exact(high_discordance, b + c)
    rate_difference = abs(prescribed - minimal) / 12 if len(valid) == 12 else 0.0
    scarcity = {
        condition: sum(
            bool(pair.get("runs", {}).get(condition, {}).get("scarcity_binding"))
            for pair in valid
        )
        for condition in ("prescribed", "minimal")
    }
    eligible = (
        controls_passed
        and len(valid) == 12
        and scarcity["prescribed"] >= 8
        and scarcity["minimal"] >= 8
    )
    higher_count = max(prescribed, minimal)
    if not eligible:
        decision = "inconclusive_invalid"
    elif rate_difference >= 0.5 and higher_count >= 8 and exact_p <= 0.05:
        decision = "large_prescription_effect"
    elif prescribed >= 8 and minimal >= 8 and abs(prescribed - minimal) <= 2:
        decision = "prescription_robust_candidate"
    else:
        decision = "ambiguous_pilot"
    direction = "none"
    if prescribed > minimal:
        direction = "prescribed_higher"
    elif minimal > prescribed:
        direction = "minimal_higher"
    return {
        "schema_version": "ae3_eval07_readout_v1",
        "decision": decision,
        "controls_passed": bool(controls_passed),
        "valid_pairs": len(valid),
        "prescribed_positive": prescribed,
        "minimal_positive": minimal,
        "prescribed_rate": prescribed / 12 if len(valid) == 12 else None,
        "minimal_rate": minimal / 12 if len(valid) == 12 else None,
        "prescribed_wilson_95": _wilson_interval(prescribed, len(valid)),
        "minimal_wilson_95": _wilson_interval(minimal, len(valid)),
        "absolute_rate_difference": rate_difference,
        "discordant_prescribed_only": b,
        "discordant_minimal_only": c,
        "effect_direction": direction,
        "exact_one_sided_p": round(exact_p, 10),
        "scarcity_binding_runs": scarcity,
    }


def _events_for_attempt(attempt: dict[str, Any], evidence: Path) -> list[dict[str, Any]]:
    relative = attempt.get("runtime_events_path")
    if not isinstance(relative, str) or not relative:
        return []
    path = evidence / relative
    if not path.is_file():
        raise RuntimeError(f"runtime events file is missing: {relative}")
    return [json.loads(raw) for raw in path.read_text(encoding="utf-8").splitlines()]


def _verify_saved_contract(
    evidence: Path,
    *,
    controls: Any,
    pairs: list[Any],
    attempts: list[Any],
    inventory: Any,
) -> dict[str, Any]:
    input_hashes: dict[str, str] = {}
    for relative, expected in FROZEN_INPUT_SHA256.items():
        bundled = evidence / "inputs" / relative.replace("/", "__")
        if not bundled.is_file():
            raise RuntimeError(f"bundled frozen input is missing: {relative}")
        observed = _sha256(bundled)
        input_hashes[relative] = observed
        if not _frozen_input_matches(relative, bundled, expected):
            raise RuntimeError(f"bundled frozen input differs: {relative}")

    bundled_cases = _read_json(
        evidence / "inputs" / CASES_PATH.replace("/", "__")
    )
    dispatch = _read_json(evidence / "dispatch_plan.json")
    if not isinstance(bundled_cases, dict) or not isinstance(dispatch, dict):
        raise TypeError("saved cases/dispatch plan are malformed")
    for key in ("pair_schedule", "conditions", "execution", "run_validity", "readout"):
        if dispatch.get(key) != bundled_cases.get(key):
            raise RuntimeError(f"dispatch plan differs from frozen cases: {key}")
    if dispatch.get("evaluation_id") != EVALUATION_ID:
        raise RuntimeError("dispatch plan evaluation id differs")
    if not isinstance(controls, dict) or controls.get("passed") is not True:
        raise RuntimeError("saved preflight controls did not pass")
    if controls.get("provider_calls") != 0:
        raise RuntimeError("saved preflight controls record provider calls")
    if not isinstance(inventory, dict):
        raise TypeError("saved run inventory is malformed")
    if inventory.get("git_revision") != dispatch.get("implementation_revision"):
        raise RuntimeError("inventory revision differs from dispatch plan")

    schedule = bundled_cases.get("pair_schedule")
    if not isinstance(schedule, list) or len(pairs) > len(schedule):
        raise RuntimeError("saved pairs exceed the frozen schedule")
    seen_cells: set[tuple[str, str]] = set()
    valid_before = 0
    for index, pair in enumerate(pairs):
        if not isinstance(pair, dict) or not isinstance(schedule[index], dict):
            raise TypeError("saved pair/schedule row is malformed")
        spec = schedule[index]
        first = str(spec.get("first_condition") or "")
        expected_order = [
            first,
            "minimal" if first == "prescribed" else "prescribed",
        ]
        expected_pair = {
            "pair_id": spec.get("pair_id"),
            "seed": spec.get("seed"),
            "role": spec.get("role"),
            "condition_order": expected_order,
        }
        observed_pair = {key: pair.get(key) for key in expected_pair}
        if observed_pair != expected_pair:
            raise RuntimeError(f"saved pair differs from frozen schedule at index {index}")
        if spec.get("role") == "reserve" and valid_before >= 12:
            raise RuntimeError("saved evidence uses a reserve pair without need")
        for condition in expected_order:
            cell = (str(pair.get("pair_id") or ""), condition)
            if cell in seen_cells:
                raise RuntimeError(f"saved seed-condition cell is duplicated: {cell}")
            seen_cells.add(cell)
        if pair.get("valid") is True and valid_before < 12:
            valid_before += 1

    if len(attempts) > 448:
        raise RuntimeError("saved attempts exceed the frozen maximum")
    ordinals = [
        attempt.get("ordinal") for attempt in attempts if isinstance(attempt, dict)
    ]
    if ordinals != list(range(1, len(attempts) + 1)):
        raise RuntimeError("saved attempt ordinals are not exact and contiguous")
    actual_cost = round(
        sum(
            float(attempt.get("cost_usd") or 0.0)
            for attempt in attempts
            if isinstance(attempt, dict)
        ),
        8,
    )
    if actual_cost > MAX_ACTUAL_COST_USD:
        raise RuntimeError("saved attempts exceed the frozen cost maximum")
    if int(inventory.get("completed_pairs", -1)) != len(pairs):
        raise RuntimeError("saved pair count differs from inventory")
    if int(inventory.get("completed_attempts", -1)) != len(attempts):
        raise RuntimeError("saved attempt count differs from inventory")
    included_pairs = sum(
        pair.get("included") is True for pair in pairs if isinstance(pair, dict)
    )
    if int(inventory.get("valid_pairs", -1)) != included_pairs:
        raise RuntimeError("saved valid-pair count differs from inventory")
    if float(inventory.get("actual_cost_usd", -1.0)) != actual_cost:
        raise RuntimeError("saved actual cost differs from inventory")
    return {
        "passed": True,
        "frozen_input_sha256": input_hashes,
        "pairs_checked": len(pairs),
        "attempts_checked": len(attempts),
        "actual_cost_usd": actual_cost,
    }


def reproduce_evidence(evidence: Path) -> dict[str, Any]:
    evidence = evidence.resolve()
    manifest = verify_manifest(evidence)
    controls = _read_json(evidence / "controls.json")
    pairs = _read_json(evidence / "pairs.json")
    attempts = _read_json(evidence / "attempts.json")
    inventory = _read_json(evidence / "run_inventory.json")
    saved_readout = _read_json(evidence / "readout.json")
    if isinstance(inventory, dict) and inventory.get("stop_reason"):
        raise RuntimeError(
            "terminal partial evidence cannot satisfy complete reproduction; "
            "verify SHA256SUMS and interruption.json instead"
        )
    if not isinstance(pairs, list) or not isinstance(attempts, list):
        raise TypeError("saved pairs/attempts are malformed")
    contract = _verify_saved_contract(
        evidence,
        controls=controls,
        pairs=pairs,
        attempts=attempts,
        inventory=inventory,
    )
    event_cache: dict[str, list[dict[str, Any]]] = {}
    attempt_errors: list[dict[str, Any]] = []
    for attempt in attempts:
        if not isinstance(attempt, dict):
            attempt_errors.append({"ordinal": None, "errors": ["attempt is not an object"]})
            continue
        relative = str(attempt.get("runtime_events_path") or "")
        if relative and relative not in event_cache:
            event_cache[relative] = _events_for_attempt(attempt, evidence)
        verified = verify_attempt_record(
            attempt,
            runtime_events=event_cache.get(relative) if relative else None,
        )
        if not verified["passed"]:
            attempt_errors.append(
                {"ordinal": attempt.get("ordinal"), "errors": verified["errors"]}
            )
    if attempt_errors:
        raise RuntimeError(f"saved attempt custody failed: {attempt_errors}")
    completed_attempts = int(inventory.get("completed_attempts", len(attempts)))
    if completed_attempts != len(attempts):
        raise RuntimeError("saved attempt count differs from inventory")

    reproduced_pairs: list[dict[str, Any]] = []
    included_count = 0
    used_ordinals: set[int] = set()
    for pair in pairs:
        if not isinstance(pair, dict):
            raise TypeError("saved pair is not an object")
        pair_id = str(pair.get("pair_id") or "")
        pair_seed = int(pair.get("seed") or -1)
        runs: dict[str, Any] = {}
        for condition in ("prescribed", "minimal"):
            saved_run = pair.get("runs", {}).get(condition)
            if not isinstance(saved_run, dict):
                raise TypeError(f"saved run is missing: {pair_id}/{condition}")
            run_attempts = [
                attempt
                for attempt in attempts
                if attempt.get("pair_id") == pair_id
                and attempt.get("condition") == condition
            ]
            if any(int(attempt.get("seed") or -1) != pair_seed for attempt in run_attempts):
                raise RuntimeError(f"saved attempt seed differs: {pair_id}/{condition}")
            used_ordinals.update(int(attempt["ordinal"]) for attempt in run_attempts)
            events_relative = str(saved_run.get("events_path") or "")
            if not events_relative or events_relative not in event_cache:
                raise RuntimeError(f"runtime events are missing for {pair_id}/{condition}")
            events = event_cache[events_relative]
            events_path = evidence / events_relative
            summary = summarize_events(events_path)
            if summary != saved_run.get("summary"):
                raise RuntimeError(
                    f"saved summary differs from runtime log: {pair_id}/{condition}"
                )
            scarcity = _scarcity_receipts(run_attempts, events)
            auxiliary = sum(
                1 for event in events if event.get("event_type") == "mint_auction"
            )
            recomputed_run = evaluate_run(
                condition=condition,
                pair_id=pair_id,
                attempts=run_attempts,
                summary=summary,
                scarcity_receipts=scarcity,
                auxiliary_provider_calls=auxiliary,
                runtime_events=events,
            )
            for key, value in recomputed_run.items():
                if saved_run.get(key) != value:
                    raise RuntimeError(
                        "saved run validity differs from reproduction: "
                        f"{pair_id}/{condition}/{key}"
                    )
            runs[condition] = {**saved_run, **recomputed_run}
        pair_valid = all(bool(runs[name]["valid"]) for name in runs)
        included = pair_valid and included_count < 12
        if included:
            included_count += 1
        if pair.get("valid") != pair_valid or pair.get("included") != included:
            raise RuntimeError(f"saved pair validity differs: {pair_id}")
        reproduced_pairs.append(
            {**pair, "valid": pair_valid, "included": included, "runs": runs}
        )
    if used_ordinals != set(range(1, len(attempts) + 1)):
        raise RuntimeError("saved attempts are not owned by exactly one scheduled cell")
    recomputed = compute_readout(
        reproduced_pairs,
        controls_passed=bool(controls.get("passed")),
    )
    if recomputed != saved_readout:
        raise RuntimeError("saved readout differs from exact reproduction")
    if not isinstance(inventory, dict) or inventory.get("readout_decision") != recomputed.get(
        "decision"
    ):
        raise RuntimeError("saved inventory decision differs from exact reproduction")
    return {
        "schema_version": "ae3_eval07_reproduction_v1",
        "passed": True,
        "manifest": manifest,
        "contract": contract,
        "attempts_verified": len(attempts),
        "readout": recomputed,
    }


def _run_local_controls(repo: Path) -> dict[str, Any]:
    args = [
        "-m",
        "pytest",
        "-q",
        "tests/test_behavioral_comparison.py",
        "tests/test_provider_qualification.py",
        "tests/test_runtime_smoke.py",
        "tests/test_emergence_report.py",
        "--tb=short",
    ]
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (completed.stdout + completed.stderr)[-12000:]
    if completed.returncode != 0:
        raise RuntimeError(f"Eval07 local controls failed before dispatch:\n{output}")
    return {"command": ["python", *args], "returncode": 0, "output": output}


def _verify_pushed_revision(repo: Path) -> str:
    revision, clean = _git_revision_and_cleanliness(repo)
    if not clean:
        raise RuntimeError("Eval07 live execution requires a clean worktree")
    completed = subprocess.run(
        ["git", "branch", "-r", "--contains", revision],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    remote_refs = [line.strip() for line in completed.stdout.splitlines() if line.strip().startswith("origin/")]
    if not remote_refs:
        raise RuntimeError("Eval07 implementation revision is not retained by origin")
    return revision


def _condition_config(
    repo: Path,
    output: Path,
    *,
    condition: str,
    seed: int,
) -> AppConfig:
    cfg = load_config(repo / CONFIG_PATH)
    cfg.llm.loop_cognition_mode = condition  # type: ignore[assignment]
    prompt = (
        "config/prompts/loop_prompt_variant.txt"
        if condition == "prescribed"
        else "config/prompts/loop_prompt_minimal.txt"
    )
    cfg.llm.loop_prompt_template_path = str(repo / prompt)
    cfg.llm.loop_policy_seed = seed
    cfg.llm.enable_bootstrap_loop_llm = True
    cfg.logging.logs_dir = str(output / "runtime_logs" / condition)
    return cfg


def _state_from_messages(messages: list[dict[str, Any]]) -> dict[str, Any] | None:
    for message in reversed(messages):
        content = message.get("content")
        if not isinstance(content, str) or "\nState:\n" not in content:
            continue
        raw = content.rsplit("\nState:\n", 1)[1]
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _scarcity_receipts(
    captures: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for event in events:
        if (
            event.get("event_type") == "loop_decision"
            and event.get("result_error_code") == "insufficient_funds"
        ):
            receipts.append(
                {
                    "reason": "insufficient_funds",
                    "sequence": event.get("sequence"),
                    "principal_id": event.get("principal_id"),
                }
            )
    for capture in captures:
        messages = capture.get("messages")
        principal_id = str(capture.get("principal_id") or "")
        if not isinstance(messages, list):
            continue
        state = _state_from_messages(messages)
        if not isinstance(state, dict):
            continue
        balance = state.get("balance")
        artifacts = state.get("artifacts")
        if not isinstance(balance, (int, float)) or not isinstance(artifacts, list):
            continue
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            owner = artifact.get("owner")
            price = artifact.get("read_price")
            if (
                isinstance(owner, str)
                and owner != principal_id
                and isinstance(price, (int, float))
                and float(price) > float(balance)
            ):
                receipts.append(
                    {
                        "reason": "unaffordable_cross_owned_paid_artifact",
                        "attempt_ordinal": capture.get("ordinal"),
                        "principal_id": principal_id,
                        "balance": float(balance),
                        "artifact_id": artifact.get("id"),
                        "read_price": float(price),
                    }
                )
                break
    return receipts


async def _run_cell(
    repo: Path,
    output: Path,
    *,
    pair_id: str,
    seed: int,
    condition: str,
    ordinal_start: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cfg = _condition_config(repo, output, condition=condition, seed=seed)
    run_id = f"eval07_{condition}_{pair_id}"
    world = World(cfg, run_id=run_id)
    runner = SimulationRunner(world)
    original_call = world.call_llm_as_syscall_async
    captures: list[dict[str, Any]] = []
    target_run_dir = output / "runtime_logs" / condition / pair_id
    target_run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = target_run_dir / "attempts.checkpoint.json"

    async def capture_call(
        *,
        payer_id: str,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        ordinal = ordinal_start + len(captures)
        result = await original_call(
            payer_id=payer_id,
            model=model,
            messages=messages,
            tools=tools,
        )
        trace_id = result.get("trace_id")
        if isinstance(trace_id, str) and trace_id:
            evidence_error: str | None = None
            try:
                receipts, call_record = _open_call_evidence(trace_id)
            except Exception as exc:  # noqa: BLE001 - checkpoint the settled call
                receipts = []
                call_record = None
                evidence_error = f"{type(exc).__name__}: {exc}"
            receipt = receipts[0] if len(receipts) == 1 else None
            capture = {
                "ordinal": ordinal,
                "pair_id": pair_id,
                "seed": seed,
                "condition": condition,
                "principal_id": payer_id,
                "messages": _json_safe(messages),
                "messages_sha256": _sha256_json(messages),
                "tools": _json_safe(tools or []),
                "tools_sha256": _sha256_json(tools or []),
                "syscall_result": _json_safe(result),
                "receipts": receipts,
                "call_record": _json_safe(call_record),
                "classification": classify_attempt(
                    principal_id=payer_id,
                    syscall_result=result,
                    receipt=receipt,
                    call_record=call_record,
                ),
                "cost_usd": receipt.get("cost_usd") if receipt is not None else None,
                "public_readback_error": evidence_error,
            }
            captures.append(capture)
            _write_json(checkpoint_path, captures)
        return result

    world.call_llm_as_syscall_async = capture_call  # type: ignore[method-assign]
    await runner.run(
        duration=float(cfg.simulation.default_duration_seconds),
        target_llm_attempts=16,
    )
    source_events = Path(world.logger.output_path)
    source_summary = Path(world.logger.summary_path)
    events = [json.loads(raw) for raw in source_events.read_text(encoding="utf-8").splitlines()]
    events_path = target_run_dir / source_events.name
    summary_path = target_run_dir / source_summary.name
    shutil.move(str(source_events), events_path)
    shutil.move(str(source_summary), summary_path)
    source_events.parent.rmdir()
    relative_events = str(events_path.relative_to(output))
    attempts: list[dict[str, Any]] = []
    for capture in captures:
        syscall_result = capture["syscall_result"]
        trace_id = syscall_result.get("trace_id")
        loop_matches = [
            event
            for event in events
            if event.get("event_type") == "loop_decision"
            and event.get("llm_trace_id") == trace_id
        ]
        loop_decision = loop_matches[0] if len(loop_matches) == 1 else None
        attempt = {
            **capture,
            "loop_decision": _json_safe(loop_decision),
            "runtime_events_path": relative_events,
        }
        attempt["verification"] = verify_attempt_record(attempt, runtime_events=events)
        attempts.append(attempt)
    _write_json(checkpoint_path, attempts)
    summary = summarize_events(events_path)
    auxiliary_provider_calls = sum(
        1 for event in events if event.get("event_type") == "mint_auction"
    )
    scarcity = _scarcity_receipts(captures, events)
    result = evaluate_run(
        condition=condition,
        pair_id=pair_id,
        attempts=attempts,
        summary=summary,
        scarcity_receipts=scarcity,
        auxiliary_provider_calls=auxiliary_provider_calls,
        runtime_events=events,
    )
    result["seed"] = seed
    result["events_path"] = relative_events
    result["elapsed_seconds"] = round(runner.elapsed_seconds, 6)
    latest = Path(cfg.logging.logs_dir) / "latest"
    if latest.is_symlink():
        latest.unlink()
    return result, attempts


def _copy_frozen_inputs(repo: Path, output: Path) -> None:
    inputs = output / "inputs"
    inputs.mkdir(parents=True)
    for relative in FROZEN_INPUT_SHA256:
        shutil.copyfile(repo / relative, inputs / relative.replace("/", "__"))


def _merge_checkpoint_attempts(
    output: Path,
    completed: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_ordinal = {int(attempt["ordinal"]): attempt for attempt in completed}
    for checkpoint in sorted((output / "runtime_logs").glob("*/*/attempts.checkpoint.json")):
        saved = _read_json(checkpoint)
        if not isinstance(saved, list):
            continue
        for attempt in saved:
            if not isinstance(attempt, dict) or not isinstance(attempt.get("ordinal"), int):
                continue
            by_ordinal.setdefault(int(attempt["ordinal"]), attempt)
    return [by_ordinal[ordinal] for ordinal in sorted(by_ordinal)]


def _interrupted_cell_events(
    output: Path,
    *,
    condition: str,
    pair_id: str,
) -> tuple[Path | None, list[dict[str, Any]]]:
    candidates = (
        output / "runtime_logs" / condition / pair_id / "events.jsonl",
        output
        / "runtime_logs"
        / condition
        / f"eval07_{condition}_{pair_id}"
        / "events.jsonl",
    )
    for path in candidates:
        if path.is_file():
            events = [
                json.loads(raw)
                for raw in path.read_text(encoding="utf-8").splitlines()
                if raw.strip()
            ]
            return path, events
    return None, []


def finalize_interrupted_evidence(
    repo: Path,
    output: Path,
    *,
    stop_reason: str,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    """Finalize a terminal interrupted Eval07 bundle without provider access."""

    repo = repo.resolve()
    output = output.resolve()
    if not stop_reason.strip():
        raise ValueError("interrupted evidence requires a non-empty stop reason")
    if (output / "run_inventory.json").exists():
        raise RuntimeError("refusing to overwrite an existing Eval07 run inventory")
    controls = _read_json(output / "controls.json")
    dispatch = _read_json(output / "dispatch_plan.json")
    if not isinstance(controls, dict) or controls.get("passed") is not True:
        raise RuntimeError("interrupted evidence lacks passing pre-dispatch controls")
    if not isinstance(dispatch, dict) or dispatch.get("evaluation_id") != EVALUATION_ID:
        raise RuntimeError("interrupted evidence lacks the frozen dispatch plan")

    raw_hashes = {
        relative: _sha256(output / relative)
        for relative in sorted(_regular_files(output))
    }
    cases = _read_json(output / "inputs" / CASES_PATH.replace("/", "__"))
    if not isinstance(cases, dict) or not isinstance(cases.get("pair_schedule"), list):
        raise TypeError("bundled Evaluation 07 schedule is malformed")

    checkpoint_attempts = _merge_checkpoint_attempts(output, [])
    ordinals = [int(attempt.get("ordinal") or -1) for attempt in checkpoint_attempts]
    if ordinals != list(range(1, len(checkpoint_attempts) + 1)):
        raise RuntimeError("interrupted attempt ordinals are not exact and contiguous")

    events_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    events_path_by_cell: dict[tuple[str, str], Path] = {}
    settled_attempts = 0
    event_cost = 0.0
    cell_inventory: list[dict[str, Any]] = []
    for spec in cases["pair_schedule"]:
        if not isinstance(spec, dict):
            continue
        pair_id = str(spec.get("pair_id") or "")
        for condition in ("prescribed", "minimal"):
            path, events = _interrupted_cell_events(
                output,
                condition=condition,
                pair_id=pair_id,
            )
            if path is None:
                continue
            cell = (pair_id, condition)
            events_by_cell[cell] = events
            events_path_by_cell[cell] = path
            settled = [
                event
                for event in events
                if event.get("event_type") in {"llm_syscall", "llm_syscall_error"}
            ]
            decisions = [
                event for event in events if event.get("event_type") == "loop_decision"
            ]
            stopped = sum(
                event.get("event_type") == "simulation_stopped" for event in events
            )
            settled_attempts += len(settled)
            event_cost += sum(float(event.get("actual_cost") or 0.0) for event in settled)
            cell_inventory.append(
                {
                    "pair_id": pair_id,
                    "condition": condition,
                    "events_path": str(path.relative_to(output)),
                    "settled_attempts": len(settled),
                    "loop_decisions": len(decisions),
                    "simulation_stopped_events": stopped,
                }
            )

    attempts: list[dict[str, Any]] = []
    for saved in checkpoint_attempts:
        attempt = deepcopy(saved)
        pair_id = str(attempt.get("pair_id") or "")
        condition = str(attempt.get("condition") or "")
        cell = (pair_id, condition)
        events = events_by_cell.get(cell, [])
        events_path = events_path_by_cell.get(cell)
        trace_id = attempt.get("syscall_result", {}).get("trace_id")
        matches = [
            event
            for event in events
            if event.get("event_type") == "loop_decision"
            and event.get("llm_trace_id") == trace_id
        ]
        attempt["loop_decision"] = matches[0] if len(matches) == 1 else None
        if events_path is not None:
            attempt["runtime_events_path"] = str(events_path.relative_to(output))
        attempt["verification"] = verify_attempt_record(
            attempt,
            runtime_events=events,
        )
        attempts.append(attempt)

    pairs: list[dict[str, Any]] = []
    included_count = 0
    for spec in cases["pair_schedule"]:
        if not isinstance(spec, dict):
            continue
        pair_id = str(spec.get("pair_id") or "")
        seed = int(spec.get("seed") or -1)
        first = str(spec.get("first_condition") or "")
        order = [first, "minimal" if first == "prescribed" else "prescribed"]
        runs: dict[str, Any] = {}
        pair_complete = True
        for condition in ("prescribed", "minimal"):
            cell = (pair_id, condition)
            events = events_by_cell.get(cell, [])
            if not events or not any(
                event.get("event_type") == "simulation_stopped" for event in events
            ):
                pair_complete = False
                break
            cell_attempts = [
                attempt
                for attempt in attempts
                if attempt.get("pair_id") == pair_id
                and attempt.get("condition") == condition
            ]
            events_path = events_path_by_cell[cell]
            summary = summarize_events(events_path)
            scarcity = _scarcity_receipts(cell_attempts, events)
            run = evaluate_run(
                condition=condition,
                pair_id=pair_id,
                attempts=cell_attempts,
                summary=summary,
                scarcity_receipts=scarcity,
                auxiliary_provider_calls=sum(
                    event.get("event_type") == "mint_auction" for event in events
                ),
                runtime_events=events,
            )
            run["seed"] = seed
            run["events_path"] = str(events_path.relative_to(output))
            runs[condition] = run
        if not pair_complete:
            break
        pair_valid = all(bool(runs[name]["valid"]) for name in ("prescribed", "minimal"))
        included = pair_valid and included_count < 12
        if included:
            included_count += 1
        pairs.append(
            {
                "pair_id": pair_id,
                "seed": seed,
                "role": spec.get("role"),
                "condition_order": order,
                "valid": pair_valid,
                "included": included,
                "runs": runs,
            }
        )

    readout = compute_readout(pairs, controls_passed=bool(controls.get("passed")))
    checkpoint_cost = round(
        sum(float(attempt.get("cost_usd") or 0.0) for attempt in attempts),
        8,
    )
    event_cost = round(event_cost, 8)
    if settled_attempts > 448 or event_cost > MAX_ACTUAL_COST_USD:
        raise RuntimeError("interrupted evidence exceeds a frozen exposure ceiling")
    observed = observed_at or datetime.now(UTC)
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=UTC)
    recovery_revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    interruption = {
        "schema_version": "ae3_eval07_interruption_v1",
        "terminal": True,
        "observed_at": observed.astimezone(UTC).isoformat(),
        "stop_reason": stop_reason.strip(),
        "further_provider_dispatch_authorized": False,
        "raw_files_before_finalization_sha256": raw_hashes,
        "cells": cell_inventory,
        "settled_provider_attempts": settled_attempts,
        "full_custody_attempt_records": len(attempts),
        "recovery_revision": recovery_revision,
    }
    inventory = {
        "schema_version": "ae3_eval07_partial_evidence_v1",
        "evaluation_id": EVALUATION_ID,
        "git_revision": dispatch.get("implementation_revision"),
        "recovery_revision": recovery_revision,
        "worktree_clean_at_dispatch": True,
        "frozen_inputs": controls.get("frozen_inputs"),
        "local_controls": {
            "passed_before_dispatch": True,
            "command_output_retained": False,
        },
        "settled_provider_attempts": settled_attempts,
        "completed_attempts": len(attempts),
        "completed_pairs": len(pairs),
        "pairs_started": len({row["pair_id"] for row in cell_inventory}),
        "valid_pairs": included_count,
        "actual_cost_usd": event_cost,
        "custody_record_cost_usd": checkpoint_cost,
        "stop_reason": stop_reason.strip(),
        "readout_decision": readout["decision"],
        "complete_reproduction_available": False,
    }
    _write_json(output / "attempts.json", attempts)
    _write_json(output / "pairs.json", pairs)
    _write_json(output / "readout.json", readout)
    _write_json(output / "interruption.json", interruption)
    _write_json(output / "run_inventory.json", inventory)
    (output / "README.md").write_text(
        "# Evaluation 07 terminal partial evidence\n\n"
        "The one-shot process ended before the frozen schedule completed. Raw "
        "events and per-attempt checkpoints are preserved; `interruption.json` "
        "records their pre-finalization hashes. This bundle is terminal and "
        "cannot support complete-result reproduction or a behavioral claim.\n",
        encoding="utf-8",
    )
    write_manifest(output)
    verify_manifest(output)
    return inventory


def _dispatch_plan(cases: dict[str, Any], revision: str) -> dict[str, Any]:
    return {
        "schema_version": "ae3_eval07_dispatch_plan_v1",
        "evaluation_id": EVALUATION_ID,
        "implementation_revision": revision,
        "pair_schedule": cases["pair_schedule"],
        "condition_contracts": cases["conditions"],
        "execution": cases["execution"],
        "run_validity": cases["run_validity"],
        "readout": cases["readout"],
    }


def run_live(
    repo: Path,
    output: Path,
    *,
    acknowledged_max_cost_usd: Decimal | None = None,
) -> dict[str, Any]:
    """Execute Evaluation 07 once after every frozen preflight passes."""

    if acknowledged_max_cost_usd != Decimal("1.68"):
        raise RuntimeError("Eval07 live execution requires exact USD 1.68 acknowledgement")
    repo = repo.resolve()
    output = output.resolve()
    existing_inventory = repo / DEFAULT_OUTPUT / "run_inventory.json"
    if existing_inventory.is_file():
        raise RuntimeError(
            "Evaluation 07 already has terminal evidence; a second live dispatch "
            "is prohibited"
        )
    if output.exists():
        raise RuntimeError(f"refusing to overwrite existing Eval07 evidence: {output}")
    frozen = verify_frozen_inputs(repo)
    revision = _verify_pushed_revision(repo)
    local_controls = _run_local_controls(repo)
    controls = run_preflight(repo)
    if not controls["passed"]:
        raise RuntimeError("Eval07 preflight controls failed before provider dispatch")
    cases = _load_cases(repo)
    output.mkdir(parents=True)
    _copy_frozen_inputs(repo, output)
    _write_json(output / "controls.json", controls)
    _write_json(output / "dispatch_plan.json", _dispatch_plan(cases, revision))

    attempts: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    valid_pairs = 0
    stop_reason: str | None = None
    try:
        for pair_spec in cases["pair_schedule"]:
            if pair_spec["role"] == "reserve" and valid_pairs >= 12:
                break
            pair_id = str(pair_spec["pair_id"])
            seed = int(pair_spec["seed"])
            first = str(pair_spec["first_condition"])
            order = [first, "minimal" if first == "prescribed" else "prescribed"]
            runs: dict[str, Any] = {}
            for condition in order:
                run_result, run_attempts = asyncio.run(
                    _run_cell(
                        repo,
                        output,
                        pair_id=pair_id,
                        seed=seed,
                        condition=condition,
                        ordinal_start=len(attempts) + 1,
                    )
                )
                attempts.extend(run_attempts)
                runs[condition] = run_result
                actual_cost = sum(float(item.get("cost_usd") or 0.0) for item in attempts)
                if len(attempts) > 448:
                    raise RuntimeError("Eval07 maximum provider attempts exceeded")
                if actual_cost > MAX_ACTUAL_COST_USD:
                    raise RuntimeError("Eval07 aggregate actual-cost ceiling exceeded")
            pair_valid = all(bool(runs[name]["valid"]) for name in ("prescribed", "minimal"))
            included = pair_valid and valid_pairs < 12
            if included:
                valid_pairs += 1
            pairs.append(
                {
                    "pair_id": pair_id,
                    "seed": seed,
                    "role": pair_spec["role"],
                    "condition_order": order,
                    "valid": pair_valid,
                    "included": included,
                    "runs": runs,
                }
            )
        if valid_pairs < 12:
            stop_reason = "fewer than 12 valid pairs after the frozen reserve schedule"
    except Exception as exc:
        stop_reason = str(exc)
        raise
    finally:
        attempts = _merge_checkpoint_attempts(output, attempts)
        readout = compute_readout(pairs, controls_passed=bool(controls["passed"]))
        inventory = {
            "schema_version": "ae3_eval07_evidence_v1",
            "evaluation_id": EVALUATION_ID,
            "git_revision": revision,
            "worktree_clean_at_dispatch": True,
            "frozen_inputs": frozen,
            "local_controls": local_controls,
            "completed_attempts": len(attempts),
            "completed_pairs": len(pairs),
            "valid_pairs": valid_pairs,
            "actual_cost_usd": round(
                sum(float(item.get("cost_usd") or 0.0) for item in attempts), 8
            ),
            "stop_reason": stop_reason,
            "readout_decision": readout["decision"],
        }
        _write_json(output / "attempts.json", attempts)
        _write_json(output / "pairs.json", pairs)
        _write_json(output / "readout.json", readout)
        _write_json(output / "run_inventory.json", inventory)
        (output / "README.md").write_text(
            "# Evaluation 07 evidence\n\n"
            "Frozen paired behavioral comparison inputs, controls, runtime logs, "
            "full call/action custody, readout, and reproduction receipt.\n",
            encoding="utf-8",
        )
        write_manifest(output)
        if stop_reason is None:
            reproduction = reproduce_evidence(output)
            _write_json(output / "reproduction.json", reproduction)
            write_manifest(output)
    result = _read_json(output / "run_inventory.json")
    if not isinstance(result, dict):  # pragma: no cover - written immediately above
        raise TypeError("run inventory is not an object")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--evaluation", type=int, choices=[7], default=7)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--reproduce", type=Path, default=None)
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--finalize-interrupted", action="store_true")
    parser.add_argument("--stop-reason", type=str, default=None)
    parser.add_argument("--acknowledge-max-cost-usd", type=Decimal, default=None)
    args = parser.parse_args(argv)
    selected = sum(
        bool(value)
        for value in (
            args.preflight,
            args.reproduce,
            args.run_live,
            args.finalize_interrupted,
        )
    )
    if selected != 1:
        raise SystemExit(
            "choose exactly one of --preflight, --reproduce, --run-live, "
            "or --finalize-interrupted"
        )
    repo = args.repo.resolve()
    if args.finalize_interrupted:
        if not args.stop_reason:
            raise SystemExit("--finalize-interrupted requires --stop-reason")
        output = args.output or Path(DEFAULT_OUTPUT)
        if not output.is_absolute():
            output = repo / output
        inventory = finalize_interrupted_evidence(
            repo,
            output,
            stop_reason=args.stop_reason,
        )
        print(json.dumps(inventory, indent=2, sort_keys=True))
        return 0
    if args.run_live:
        if args.acknowledge_max_cost_usd != Decimal("1.68"):
            raise SystemExit(
                "live dispatch requires exact --acknowledge-max-cost-usd 1.68"
            )
        output = args.output or Path(DEFAULT_OUTPUT)
        if not output.is_absolute():
            output = repo / output
        inventory = run_live(
            repo,
            output,
            acknowledged_max_cost_usd=args.acknowledge_max_cost_usd,
        )
        print(json.dumps(inventory, indent=2, sort_keys=True))
        return 0
    if args.preflight:
        print(json.dumps(run_preflight(repo), indent=2, sort_keys=True))
        return 0
    if args.reproduce is None:  # pragma: no cover - selected invariant
        raise SystemExit("--reproduce requires an evidence path")
    evidence = args.reproduce
    if not evidence.is_absolute():
        evidence = repo / evidence
    print(json.dumps(reproduce_evidence(evidence), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
