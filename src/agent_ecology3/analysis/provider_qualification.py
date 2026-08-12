"""Frozen provider/prompt/tool qualifications for Evaluations 05 and 06."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import inspect
import json
import shutil
import subprocess
import sys
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from ..config import AppConfig, load_config
from ..world.actions import parse_intent_from_json
from ..world.world import World

CONDITION_PROMPTS = {
    "prescribed": "config/prompts/loop_prompt_variant.txt",
    "minimal": "config/prompts/loop_prompt_minimal.txt",
}


@dataclass(frozen=True)
class QualificationSpec:
    evaluation_id: int
    config_path: str
    state_path: str
    preregistration_path: str
    output_path: str
    frozen_input_sha256: dict[str, str]


EVALUATION_05 = QualificationSpec(
    evaluation_id=5,
    config_path="config/config.provider_qualification.yaml",
    state_path="config/evaluations/05_fixed_state.json",
    preregistration_path="docs/evaluations/05_provider_tool_qualification.md",
    output_path="docs/evaluations/evidence/05_provider_tool_qualification",
    frozen_input_sha256={
        "config/config.provider_qualification.yaml": (
            "769be03a6ad5befdbf8553523df284b8018ba7e2f0f910a622068d65677e6228"
        ),
        "config/evaluations/05_fixed_state.json": (
            "0cd6a09cc8dc03dffbf8a5a2d4cb0678ce749af20afa53ff5d4c07466f80ff9e"
        ),
        "config/prompts/loop_prompt_variant.txt": (
            "1c0219c4dc5dcf2aa0fb64b756546a4fa583c4e40a9f99108c7921a4b7fbc4b2"
        ),
        "config/prompts/loop_prompt_minimal.txt": (
            "c1029d2fda78e6309de66d229c9a872bf17a23f11465f94106aed7a88792f96a"
        ),
        "docs/evaluations/05_provider_tool_qualification.md": (
            "4230fef9613e22184070ad95c1a1060a3a4669bdfec1eb46b0b117cf1e32e6a4"
        ),
    },
)

EVALUATION_06 = QualificationSpec(
    evaluation_id=6,
    config_path="config/config.provider_qualification_06.yaml",
    state_path="config/evaluations/06_fixed_state.json",
    preregistration_path="docs/evaluations/06_public_readback_qualification.md",
    output_path="docs/evaluations/evidence/06_public_readback_qualification",
    frozen_input_sha256={
        "config/config.provider_qualification_06.yaml": (
            "e222afa03187e08fb945b589cf51bda72f9160eb94092ba5010df8cf4117a346"
        ),
        "config/evaluations/06_fixed_state.json": (
            "c1792e2c64e5b990198c3b9acfaa6e5703db4a86319365a32ad20ecb8a6acb9a"
        ),
        "config/prompts/loop_prompt_variant.txt": (
            "1c0219c4dc5dcf2aa0fb64b756546a4fa583c4e40a9f99108c7921a4b7fbc4b2"
        ),
        "config/prompts/loop_prompt_minimal.txt": (
            "c1029d2fda78e6309de66d229c9a872bf17a23f11465f94106aed7a88792f96a"
        ),
        "docs/evaluations/06_public_readback_qualification.md": (
            "ee93182bd502b98176325af7619ab88a5b9a6deb3d51cd047595f84bb1b5e730"
        ),
    },
)

EVALUATION_SPECS = {5: EVALUATION_05, 6: EVALUATION_06}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _extract_json_object(text: Any) -> dict[str, Any] | None:
    if not isinstance(text, str):
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _parse_tool_action(
    tool_calls: list[Any],
) -> tuple[dict[str, Any] | None, str | None]:
    matching: list[Any] = []
    for entry in tool_calls:
        if not isinstance(entry, dict):
            continue
        function = entry.get("function")
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if isinstance(name, str) and (
            name.strip().lower() == "ae3_action"
            or name.strip().lower().endswith("ae3_action")
        ):
            matching.append(function)
    if len(matching) != 1:
        return None, "expected exactly one ae3_action tool call"
    arguments = matching[0].get("arguments")
    if isinstance(arguments, dict):
        return arguments, None
    if not isinstance(arguments, str):
        return None, "tool arguments are not a JSON object or string"
    try:
        parsed = json.loads(arguments)
    except json.JSONDecodeError:
        parsed = _extract_json_object(arguments)
    if not isinstance(parsed, dict):
        return None, "tool arguments do not decode to an object"
    return parsed, None


def _classification(
    terminal_class: str,
    *,
    usable: bool = False,
    action: dict[str, Any] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "terminal_class": terminal_class,
        "usable": usable,
        "action": action,
        "reason": reason,
    }


def classify_attempt(
    *,
    principal_id: str,
    syscall_result: dict[str, Any],
    receipt: dict[str, Any] | None,
    call_record: dict[str, Any] | None,
) -> dict[str, Any]:
    """Classify one frozen qualification attempt without response repair."""

    trace_id = syscall_result.get("trace_id")
    if (
        not isinstance(trace_id, str)
        or not trace_id
        or receipt is None
        or call_record is None
    ):
        return _classification(
            "trace_failure", reason="missing trace, receipt, or exact call record"
        )
    finish_reason = str(receipt.get("finish_reason") or "").strip().lower()
    error_text = str(syscall_result.get("error") or "").strip().lower()
    error_type = str(receipt.get("error_type") or "").strip().lower()
    if finish_reason in {"length", "max_tokens"} or any(
        marker in error_text
        for marker in (
            "maximum output",
            "max_tokens",
            "max tokens",
            "truncat",
            "finish_reason=length",
        )
    ):
        return _classification("output_truncation", reason=error_text or finish_reason)
    if "timeout" in error_text or "timeout" in error_type or "timed out" in error_text:
        return _classification("provider_timeout", reason=error_text or error_type)
    if not bool(syscall_result.get("success")):
        return _classification(
            "provider_error", reason=error_text or error_type or "provider failure"
        )

    persistence = call_record.get("content_persistence")
    if persistence is not None and persistence != "full":
        return _classification(
            "custody_failure",
            reason="exact call record was not retained under full-content persistence",
        )
    if (
        "response" not in call_record
        or call_record.get("response") != syscall_result.get("content")
    ):
        return _classification(
            "custody_failure",
            reason="caller-visible and retained response content differ",
        )

    raw_tool_calls = syscall_result.get("tool_calls")
    tool_calls = raw_tool_calls if isinstance(raw_tool_calls, list) else []
    if tool_calls:
        stored_tool_calls = call_record.get("response_tool_calls")
        if stored_tool_calls != tool_calls:
            return _classification(
                "custody_failure",
                reason="caller-visible and retained response_tool_calls differ",
            )
        action, parse_error = _parse_tool_action(tool_calls)
        if action is None:
            return _classification("missing_or_malformed_action", reason=parse_error)
        parsed_intent = parse_intent_from_json(principal_id, json.dumps(action))
        if isinstance(parsed_intent, str):
            return _classification(
                "illegal_action", action=action, reason=parsed_intent
            )
        return _classification("usable_tool_action", usable=True, action=action)

    action = _extract_json_object(syscall_result.get("content"))
    if action is None:
        return _classification(
            "missing_or_malformed_action",
            reason="no ae3_action tool call or JSON action object",
        )
    parsed_intent = parse_intent_from_json(principal_id, json.dumps(action))
    if isinstance(parsed_intent, str):
        return _classification("illegal_action", action=action, reason=parsed_intent)
    return _classification("usable_json_action", usable=True, action=action)


def _verify_frozen_inputs(
    repo: Path,
    spec: QualificationSpec = EVALUATION_05,
) -> dict[str, str]:
    observed: dict[str, str] = {}
    for relative, expected in spec.frozen_input_sha256.items():
        digest = _sha256(repo / relative)
        observed[relative] = digest
        if digest != expected:
            raise RuntimeError(
                f"frozen input mismatch for {relative}: expected {expected}, observed {digest}"
            )
    return observed


def _git_revision_and_cleanliness(repo: Path) -> tuple[str, bool]:
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=repo, text=True
    )
    return revision, not bool(status.strip())


def _run_local_controls(repo: Path) -> dict[str, Any]:
    test_args = [
        "-m",
        "pytest",
        "-q",
        "tests/test_provider_qualification.py",
        "tests/test_runtime_smoke.py",
        "--tb=short",
    ]
    command = [
        sys.executable,
        *test_args,
    ]
    completed = subprocess.run(
        command,
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (completed.stdout + completed.stderr)[-8000:]
    if completed.returncode != 0:
        raise RuntimeError(f"local controls failed before dispatch:\n{output}")
    return {
        "command": ["python", *test_args],
        "returncode": completed.returncode,
        "output": output,
    }


def _condition_config(
    repo: Path,
    condition: str,
    output: Path,
    spec: QualificationSpec = EVALUATION_05,
) -> AppConfig:
    cfg = load_config(repo / spec.config_path)
    cfg.llm.loop_cognition_mode = condition  # type: ignore[assignment]
    cfg.llm.loop_prompt_template_path = str(repo / CONDITION_PROMPTS[condition])
    cfg.logging.logs_dir = str(output / "runtime_logs")
    return cfg


def _fixed_state(
    repo: Path,
    principal_id: str,
    spec: QualificationSpec = EVALUATION_05,
) -> dict[str, Any]:
    raw = (repo / spec.state_path).read_text()
    loaded = json.loads(raw.replace("${principal_id}", principal_id))
    if not isinstance(loaded, dict):  # pragma: no cover - frozen input invariant
        raise TypeError("fixed state must be an object")
    return loaded


def _build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    ordinal = 0
    for round_number in range(1, 5):
        for principal_number in range(1, 5):
            for condition in ("prescribed", "minimal"):
                ordinal += 1
                cases.append(
                    {
                        "ordinal": ordinal,
                        "round": round_number,
                        "condition": condition,
                        "principal_id": f"alpha_{principal_number}",
                    }
                )
    return cases


def _open_call_evidence(
    trace_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    from llm_client.observability.query import get_llm_call_receipts
    from llm_client.observability.replay import get_call_record

    receipts = get_llm_call_receipts(trace_id=trace_id)
    serialized = [receipt.model_dump(mode="json") for receipt in receipts]
    if len(receipts) != 1:
        return serialized, None
    call_id = int(receipts[0].receipt_id.rsplit("-", 1)[1])
    return serialized, get_call_record(call_id)


def _verify_shared_custody_schema() -> None:
    from llm_client import io_log

    columns = {
        str(row[1]) for row in io_log._get_db().execute("PRAGMA table_info(llm_calls)")
    }
    required = {"response_tool_calls", "n_tool_calls"}
    missing = required - columns
    if missing:
        raise RuntimeError(f"shared-client tool custody schema is missing: {sorted(missing)}")
    default = inspect.signature(io_log.log_call).parameters[
        "content_persistence"
    ].default
    if default != "full":
        raise RuntimeError(
            "shared-client default content persistence is not full-content custody"
        )


def _control_tool_call() -> dict[str, Any]:
    return {
        "id": "eval06-public-readback-control",
        "type": "function",
        "function": {
            "name": "ae3_action",
            "arguments": (
                '{"action_type":"query_kernel","query_type":"resources",'
                '"params":{}}'
            ),
        },
    }


def run_public_readback_control(database_path: Path) -> dict[str, Any]:
    """Exercise real local persistence and public readback without a provider call."""

    from llm_client import configure_logging, io_log
    from llm_client.core.data_types import LLMCallResult

    database_path = database_path.resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    configure_logging(
        enabled=True,
        data_root=database_path.parent / "jsonl",
        project="agent_ecology3_eval06_public_readback_control",
        db_path=database_path,
    )
    tool_call = _control_tool_call()
    messages = [{"role": "user", "content": "synthetic zero-spend custody control"}]
    result = LLMCallResult(
        content="",
        usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        cost=0.0,
        model="control/no-provider",
        tool_calls=[tool_call],
        finish_reason="tool_calls",
        cost_source="zero_spend_control",
        marginal_cost=0.0,
    )

    records: dict[str, dict[str, Any]] = {}
    try:
        for name, persistence in (("positive", "full"), ("redaction", "metadata_only")):
            trace_id = f"ae3/eval06/control/{name}"
            io_log.log_call(
                model="control/no-provider",
                messages=messages,
                result=result,
                latency_s=0.001,
                caller="eval06_public_readback_control",
                task="agent_ecology3_eval06_control",
                trace_id=trace_id,
                retry_count=0,
                content_persistence=persistence,
            )
            receipts, call_record = _open_call_evidence(trace_id)
            receipt = receipts[0] if len(receipts) == 1 else None
            syscall_result = {
                "success": True,
                "trace_id": trace_id,
                "content": "",
                "tool_calls": [tool_call],
            }
            records[name] = {
                "syscall_result": syscall_result,
                "receipts": receipts,
                "call_record": _json_safe(call_record),
                "classification": classify_attempt(
                    principal_id="alpha_1",
                    syscall_result=syscall_result,
                    receipt=receipt,
                    call_record=call_record,
                ),
            }

        corrupted_record = deepcopy(records["positive"]["call_record"])
        corrupted_record["response_tool_calls"] = []
        positive_receipt = records["positive"]["receipts"][0]
        records["corruption"] = {
            "syscall_result": records["positive"]["syscall_result"],
            "receipts": records["positive"]["receipts"],
            "call_record": corrupted_record,
            "classification": classify_attempt(
                principal_id="alpha_1",
                syscall_result=records["positive"]["syscall_result"],
                receipt=positive_receipt,
                call_record=corrupted_record,
            ),
        }
        storage_rows = io_log._get_db().execute(
            "SELECT trace_id, content_persistence FROM llm_calls ORDER BY id"
        ).fetchall()
    finally:
        io_log.close()

    expected = {
        "positive": "usable_tool_action",
        "redaction": "custody_failure",
        "corruption": "custody_failure",
    }
    observed = {
        name: str(record["classification"]["terminal_class"])
        for name, record in records.items()
    }
    costs = [
        float(receipt.get("cost_usd") or 0.0)
        for record in records.values()
        for receipt in record["receipts"]
    ]
    passed = observed == expected and all(cost == 0.0 for cost in costs)
    return {
        "schema_version": "ae3_eval06_public_readback_control_v1",
        "control_type": "synthetic_local_persistence_no_provider",
        "provider_calls": 0,
        "expected_terminal_classes": expected,
        "observed_terminal_classes": observed,
        "zero_cost": all(cost == 0.0 for cost in costs),
        "passed": passed,
        "public_positive_record_has_content_persistence": (
            "content_persistence" in records["positive"]["call_record"]
        ),
        "storage_policies": {str(row[0]): str(row[1]) for row in storage_rows},
        "database_sha256": _sha256(database_path),
        "records": records,
    }


def _run_public_readback_control_isolated(repo: Path) -> dict[str, Any]:
    with TemporaryDirectory(prefix="ae3-eval06-control-") as temp_dir:
        database_path = Path(temp_dir) / "control.sqlite3"
        command = [
            sys.executable,
            "-m",
            "agent_ecology3.analysis.provider_qualification",
            "--control-worker",
            "--control-db",
            str(database_path),
        ]
        completed = subprocess.run(
            command,
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stdout + completed.stderr)[-8000:]
            raise RuntimeError(f"public readback control process failed:\n{detail}")
        try:
            loaded = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("public readback control returned malformed JSON") from exc
        if not isinstance(loaded, dict):
            raise TypeError("public readback control did not return an object")
        return loaded


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _write_manifest(output: Path) -> None:
    manifest = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            manifest.append(f"{_sha256(path)}  {path.relative_to(output)}")
    (output / "SHA256SUMS").write_text("\n".join(manifest) + "\n")


def _copy_frozen_inputs(repo: Path, output: Path, spec: QualificationSpec) -> None:
    inputs_dir = output / "inputs"
    inputs_dir.mkdir()
    for relative in spec.frozen_input_sha256:
        source = repo / relative
        destination = inputs_dir / relative.replace("/", "__")
        shutil.copyfile(source, destination)


def _write_invalid_control_evidence(
    *,
    repo: Path,
    output: Path,
    spec: QualificationSpec,
    revision: str,
    clean: bool,
    frozen_hashes: dict[str, str],
    local_controls: dict[str, Any],
    public_control: dict[str, Any],
) -> None:
    output.mkdir(parents=True)
    _copy_frozen_inputs(repo, output, spec)
    _write_json(output / "public_readback_control.json", public_control)
    _write_json(
        output / "run_inventory.json",
        {
            "schema_version": f"ae3_evaluation_{spec.evaluation_id:02d}_evidence_v1",
            "evaluation_id": spec.evaluation_id,
            "git_revision": revision,
            "worktree_clean_at_dispatch": clean,
            "frozen_input_sha256": frozen_hashes,
            "local_controls": local_controls,
            "public_readback_control": public_control,
            "planned_attempts": 32,
            "completed_attempts": 0,
            "summary": {
                "verdict": "invalid_assay",
                "actual_cost_usd": 0.0,
                "stop_reason": "public readback controls failed before provider dispatch",
            },
        },
    )
    (output / "README.md").write_text(
        f"# Evaluation {spec.evaluation_id:02d} invalid preflight evidence\n\n"
        "Public-readback controls failed before provider dispatch.\n"
    )
    _write_manifest(output)


def _summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    conditions: dict[str, Any] = {}
    for condition in ("prescribed", "minimal"):
        rows = [row for row in records if row["case"]["condition"] == condition]
        classes = Counter(row["classification"]["terminal_class"] for row in rows)
        usable = sum(1 for row in rows if row["classification"]["usable"])
        conditions[condition] = {
            "attempts": len(rows),
            "usable": usable,
            "usable_rate": usable / len(rows) if rows else 0.0,
            "terminal_classes": dict(sorted(classes.items())),
            "qualified": (
                len(rows) == 16
                and usable >= 15
                and classes["provider_timeout"] == 0
                and classes["output_truncation"] == 0
                and classes["trace_failure"] == 0
                and classes["custody_failure"] == 0
            ),
        }
    qualified = all(value["qualified"] for value in conditions.values())
    return {
        "conditions": conditions,
        "verdict": "qualified" if qualified else "not_qualified",
        "actual_cost_usd": sum(float(row.get("cost_usd") or 0.0) for row in records),
    }


async def run_live(
    repo: Path,
    output: Path,
    spec: QualificationSpec = EVALUATION_05,
    *,
    public_control: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the frozen serial assay once and write its evidence bundle."""

    if output.exists():
        raise RuntimeError(f"refusing to overwrite existing evidence: {output}")
    frozen_hashes = _verify_frozen_inputs(repo, spec)
    revision, clean = _git_revision_and_cleanliness(repo)
    if not clean:
        raise RuntimeError("live qualification requires a clean worktree")
    controls = _run_local_controls(repo)
    _verify_shared_custody_schema()
    if spec.evaluation_id == 6:
        public_control = public_control or _run_public_readback_control_isolated(repo)
        if not bool(public_control.get("passed")):
            _write_invalid_control_evidence(
                repo=repo,
                output=output,
                spec=spec,
                revision=revision,
                clean=clean,
                frozen_hashes=frozen_hashes,
                local_controls=controls,
                public_control=public_control,
            )
            raise RuntimeError("public readback controls failed before provider dispatch")

    output.mkdir(parents=True)
    _copy_frozen_inputs(repo, output, spec)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    worlds: dict[str, World] = {}
    effective_configs: dict[str, dict[str, Any]] = {}
    tools = World.build_loop_action_tools()
    for condition, prompt_path in CONDITION_PROMPTS.items():
        cfg = _condition_config(repo, condition, output, spec)
        worlds[condition] = World(
            cfg,
            run_id=f"eval{spec.evaluation_id:02d}_{condition}_{timestamp}",
        )
        effective = cfg.model_dump(mode="json")
        effective["llm"]["loop_prompt_template_path"] = prompt_path
        effective["logging"]["logs_dir"] = "<evidence>/runtime_logs"
        effective_configs[condition] = effective

    dispatch_plan: list[dict[str, Any]] = []
    for case in _build_cases():
        condition = str(case["condition"])
        principal_id = str(case["principal_id"])
        world = worlds[condition]
        strategy = world.artifacts.get(f"{principal_id}_strategy")
        if strategy is None:  # pragma: no cover - bootstrap invariant
            raise RuntimeError(f"missing strategy for {principal_id}")
        messages = world.build_loop_messages(
            principal_id=principal_id,
            state_snapshot=_fixed_state(repo, principal_id, spec),
            strategy_text=strategy.content,
        )
        dispatch_plan.append(
            {
                "case": case,
                "messages": messages,
                "messages_sha256": _sha256_json(messages),
                "tools": tools,
                "tools_sha256": _sha256_json(tools),
            }
        )
    _write_json(output / "dispatch_plan.json", dispatch_plan)
    if public_control is not None:
        _write_json(output / "public_readback_control.json", public_control)

    records: list[dict[str, Any]] = []
    stop_reason: str | None = None
    for planned in dispatch_plan:
        case = planned["case"]
        condition = str(case["condition"])
        principal_id = str(case["principal_id"])
        world = worlds[condition]
        world.event_number += 1
        messages = planned["messages"]
        syscall_result = await world.call_llm_as_syscall_async(
            payer_id=principal_id,
            model=world.config.llm.default_model,
            messages=messages,
            tools=tools,
        )
        trace_id = syscall_result.get("trace_id")
        receipts: list[dict[str, Any]] = []
        call_record: dict[str, Any] | None = None
        if isinstance(trace_id, str) and trace_id:
            receipts, call_record = _open_call_evidence(trace_id)
        receipt = receipts[0] if len(receipts) == 1 else None
        classification = classify_attempt(
            principal_id=principal_id,
            syscall_result=syscall_result,
            receipt=receipt,
            call_record=call_record,
        )
        cost_usd = receipt.get("cost_usd") if receipt is not None else None
        records.append(
            {
                "case": case,
                "messages": messages,
                "messages_sha256": planned["messages_sha256"],
                "tools": tools,
                "tools_sha256": planned["tools_sha256"],
                "syscall_result": _json_safe(syscall_result),
                "receipts": receipts,
                "call_record": _json_safe(call_record),
                "classification": classification,
                "cost_usd": cost_usd,
            }
        )
        if syscall_result.get("error_code") == "insufficient_budget":
            stop_reason = (
                f"provider budget exhausted in {condition} at case {case['ordinal']}"
            )
            break

    summary = _summarize(records)
    if stop_reason is not None:
        summary["verdict"] = "invalid_assay"
    summary["stop_reason"] = stop_reason

    inventory = {
        "schema_version": f"ae3_evaluation_{spec.evaluation_id:02d}_evidence_v1",
        "evaluation_id": spec.evaluation_id,
        "git_revision": revision,
        "worktree_clean_at_dispatch": clean,
        "frozen_input_sha256": frozen_hashes,
        "effective_configs": effective_configs,
        "effective_config_sha256": {
            condition: _sha256_json(config)
            for condition, config in effective_configs.items()
        },
        "tool_schema_sha256": _sha256_json(tools),
        "model": "minimax/minimax-m3",
        "planned_attempts": 32,
        "completed_attempts": len(records),
        "local_controls": controls,
        "public_readback_control": public_control,
        "summary": summary,
    }
    _write_json(output / "attempts.json", records)
    _write_json(output / "run_inventory.json", inventory)
    (output / "README.md").write_text(
        f"# Evaluation {spec.evaluation_id:02d} evidence\n\n"
        "Frozen provider/prompt/tool qualification inputs, exact shared-client "
        "call records, classifications, and manifest.\n"
    )

    _write_manifest(output)
    return inventory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--evaluation",
        type=int,
        choices=sorted(EVALUATION_SPECS),
        default=5,
    )
    parser.add_argument(
        "--run-live",
        action="store_true",
        help="Acknowledge that the frozen command will make paid provider calls.",
    )
    parser.add_argument("--control-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--control-db", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.control_worker:
        if args.control_db is None:
            raise SystemExit("--control-worker requires --control-db")
        print(json.dumps(run_public_readback_control(args.control_db), sort_keys=True))
        return
    if not args.run_live:
        raise SystemExit("refusing provider dispatch without --run-live")
    repo = args.repo.resolve()
    spec = EVALUATION_SPECS[args.evaluation]
    output = args.output or Path(spec.output_path)
    if not output.is_absolute():
        output = repo / output
    inventory = asyncio.run(run_live(repo, output.resolve(), spec))
    print(json.dumps(inventory["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
