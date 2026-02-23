"""Run the standard phase1 forced-explore matrix and cohort comparison."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def _parse_conditions(raw: str) -> list[str]:
    values = [item.strip().lower() for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("--conditions must include at least one condition")
    allowed = {"baseline", "reduced", "off"}
    unknown = sorted({item for item in values if item not in allowed})
    if unknown:
        raise ValueError(f"unsupported condition(s): {', '.join(unknown)}")
    return values


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run phase1 baseline/reduced/off suite with cohort compare")
    parser.add_argument("--config", default="config/config.yaml", help="Path to AE3 config YAML")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--duration", type=float, default=900.0)
    parser.add_argument("--agents", type=int, default=4)
    parser.add_argument("--model", default=None)
    parser.add_argument("--subscription-estimated-cost-multiplier", type=float, default=None)
    parser.add_argument("--llm-loop", choices=("on", "off"), default="on")
    parser.add_argument("--loop-llm-cooldown", type=float, default=0.0)
    parser.add_argument("--loop-prompt-template", default=None)
    parser.add_argument("--target-llm-calls", type=int, default=80)
    parser.add_argument("--seed-base", type=int, default=1000)
    parser.add_argument("--seed-step", type=int, default=1)
    parser.add_argument("--llm-preflight", choices=("auto", "on", "off"), default="auto")
    parser.add_argument("--min-llm-calls", type=int, default=1)
    parser.add_argument("--min-llm-valid-decisions", type=int, default=5)
    parser.add_argument("--min-llm-attempt-rate", type=float, default=None)
    parser.add_argument("--min-llm-valid-decision-rate", type=float, default=None)
    parser.add_argument("--invalid-run-policy", choices=("warn", "drop", "fail"), default="drop")
    parser.add_argument("--gate-policy", default="@config/gates/phase1_matrix_gate.json")
    parser.add_argument("--conditions", default="baseline,reduced,off")
    parser.add_argument("--experiment-dataset", default="agent_ecology3_emergence")
    parser.add_argument("--experiment-project", default="agent_ecology3")
    parser.add_argument("--experiment-phase", default="phase1")
    parser.add_argument("--experiment-scenario-id", default=None)
    parser.add_argument("--llm-client-repo", default="/home/brian/projects/llm_client")
    parser.add_argument("--output-dir", default="logs")
    parser.add_argument("--prefix", default="phase1_suite")
    parser.add_argument("--strict-exit", action="store_true", help="Exit non-zero when any condition exits non-zero")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def _resolve_summary_path(output_dir: Path, prefix: str) -> Path | None:
    candidates = sorted(
        output_dir.glob(f"{prefix}_*_summary.json"),
        key=lambda p: (p.stat().st_mtime, p.name),
    )
    if not candidates:
        return None
    return candidates[-1]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def _ensure_llm_client_import(repo_path: str | None) -> None:
    if not repo_path:
        return
    candidate = Path(repo_path).expanduser().resolve()
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


def _compare_cohorts(
    *,
    dataset: str,
    project: str,
    scenario_id: str,
    phase: str,
    condition_ids: list[str],
    baseline_condition_id: str,
) -> dict[str, Any]:
    from llm_client import compare_cohorts

    return compare_cohorts(
        dataset=dataset,
        project=project,
        scenario_id=scenario_id,
        phase=phase,
        condition_ids=condition_ids,
        baseline_condition_id=baseline_condition_id,
        limit=2000,
    )


def _run_condition(args: argparse.Namespace, *, scenario_id: str, condition: str) -> dict[str, Any]:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"{args.prefix}_{scenario_id}_{condition}"
    run_log_path = output_dir / f"{prefix}_driver.log"
    cmd = [
        sys.executable,
        "-m",
        "agent_ecology3.analysis.scarcity_matrix",
        "--config",
        str(args.config),
        "--runs",
        str(int(args.runs)),
        "--duration",
        str(float(args.duration)),
        "--agents",
        str(int(args.agents)),
        "--llm-loop",
        str(args.llm_loop),
        "--loop-forced-explore",
        condition,
        "--target-llm-calls",
        str(int(args.target_llm_calls)),
        "--seed-base",
        str(int(args.seed_base)),
        "--seed-step",
        str(int(args.seed_step)),
        "--llm-preflight",
        str(args.llm_preflight),
        "--min-llm-calls",
        str(int(args.min_llm_calls)),
        "--min-llm-valid-decisions",
        str(int(args.min_llm_valid_decisions)),
        "--invalid-run-policy",
        str(args.invalid_run_policy),
        "--experiment-dataset",
        str(args.experiment_dataset),
        "--experiment-project",
        str(args.experiment_project),
        "--experiment-condition-id",
        condition,
        "--experiment-scenario-id",
        scenario_id,
        "--experiment-phase",
        str(args.experiment_phase),
        "--llm-client-repo",
        str(args.llm_client_repo),
        "--output-dir",
        str(output_dir),
        "--prefix",
        prefix,
        "--log-experiment",
    ]
    if args.model:
        cmd.extend(["--model", str(args.model)])
    if args.subscription_estimated_cost_multiplier is not None:
        cmd.extend(["--subscription-estimated-cost-multiplier", str(float(args.subscription_estimated_cost_multiplier))])
    if args.loop_llm_cooldown is not None:
        cmd.extend(["--loop-llm-cooldown", str(float(args.loop_llm_cooldown))])
    if args.loop_prompt_template:
        cmd.extend(["--loop-prompt-template", str(args.loop_prompt_template)])
    if args.min_llm_attempt_rate is not None:
        cmd.extend(["--min-llm-attempt-rate", str(float(args.min_llm_attempt_rate))])
    if args.min_llm_valid_decision_rate is not None:
        cmd.extend(["--min-llm-valid-decision-rate", str(float(args.min_llm_valid_decision_rate))])
    if args.gate_policy:
        cmd.extend(["--gate-policy", str(args.gate_policy), "--gate-fail-exit-code"])

    started_at = time.time()
    with run_log_path.open("w", encoding="utf-8") as run_log:
        proc = subprocess.run(cmd, check=False, stdout=run_log, stderr=subprocess.STDOUT)
    finished_at = time.time()
    summary_path = _resolve_summary_path(output_dir, prefix)
    summary = _load_json(summary_path) if summary_path is not None else None
    return {
        "condition": condition,
        "command": cmd,
        "exit_code": int(proc.returncode),
        "duration_seconds": round(finished_at - started_at, 3),
        "summary_path": str(summary_path.resolve()) if summary_path else None,
        "run_log_path": str(run_log_path.resolve()),
        "summary": summary,
    }


def main() -> int:
    args = _parse_args()
    conditions = _parse_conditions(str(args.conditions))
    scenario_id = (
        str(args.experiment_scenario_id).strip()
        if isinstance(args.experiment_scenario_id, str) and args.experiment_scenario_id.strip()
        else f"phase1_suite_{int(time.time())}"
    )

    records: list[dict[str, Any]] = []
    for condition in conditions:
        print(f"[phase1-suite] running condition={condition}")
        record = _run_condition(args, scenario_id=scenario_id, condition=condition)
        print(
            f"[phase1-suite] condition={condition} exit={record['exit_code']} "
            f"log={record['run_log_path']}"
        )
        records.append(record)

    _ensure_llm_client_import(args.llm_client_repo)
    compare_payload = _compare_cohorts(
        dataset=str(args.experiment_dataset),
        project=str(args.experiment_project),
        scenario_id=scenario_id,
        phase=str(args.experiment_phase),
        condition_ids=conditions,
        baseline_condition_id="baseline" if "baseline" in conditions else conditions[0],
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    suite_path = output_dir / f"{args.prefix}_{scenario_id}_suite.json"
    payload = {
        "scenario_id": scenario_id,
        "phase": str(args.experiment_phase),
        "dataset": str(args.experiment_dataset),
        "project": str(args.experiment_project),
        "conditions": conditions,
        "records": records,
        "compare_cohorts": compare_payload,
        "suite_path": str(suite_path.resolve()),
    }
    suite_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"[phase1-suite] suite={suite_path.resolve()}")

    if args.strict_exit:
        bad = [row for row in records if int(row.get("exit_code", 0)) != 0]
        if bad:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
