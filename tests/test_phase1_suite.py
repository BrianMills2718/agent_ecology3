from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pytest

from agent_ecology3.analysis.phase1_suite import _parse_conditions, _resolve_summary_path, _run_condition


def test_parse_conditions_accepts_supported_values() -> None:
    assert _parse_conditions("baseline,reduced,off") == ["baseline", "reduced", "off"]
    assert _parse_conditions(" baseline , OFF ") == ["baseline", "off"]


def test_parse_conditions_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="unsupported condition"):
        _parse_conditions("baseline,custom")
    with pytest.raises(ValueError, match="must include at least one"):
        _parse_conditions("   ")


def test_resolve_summary_path_picks_most_recent(tmp_path: Path) -> None:
    older = tmp_path / "phase1_suite_demo_baseline_111_summary.json"
    newer = tmp_path / "phase1_suite_demo_baseline_222_summary.json"
    older.write_text(json.dumps({"old": True}), encoding="utf-8")
    newer.write_text(json.dumps({"new": True}), encoding="utf-8")
    older.touch()
    newer.touch()

    resolved = _resolve_summary_path(tmp_path, "phase1_suite_demo_baseline")
    assert resolved == newer


def test_resolve_summary_path_returns_none_when_missing(tmp_path: Path) -> None:
    assert _resolve_summary_path(tmp_path, "missing_prefix") is None


def test_run_condition_uses_unbuffered_python_for_child_runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured_cmd: list[str] = []

    def _fake_run(cmd, check, stdout, stderr):  # type: ignore[no-untyped-def]
        del check, stdout, stderr
        captured_cmd.extend(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("agent_ecology3.analysis.phase1_suite.subprocess.run", _fake_run)

    summary_path = tmp_path / "phase1_suite_demo_baseline_123_summary.json"
    summary_path.write_text(json.dumps({"ok": True}), encoding="utf-8")

    args = argparse.Namespace(
        output_dir=str(tmp_path),
        prefix="phase1_suite",
        config="config/config.yaml",
        runs=1,
        duration=30.0,
        agents=4,
        llm_loop="on",
        target_llm_calls=10,
        seed_base=1000,
        seed_step=1,
        llm_preflight="auto",
        min_llm_calls=1,
        min_llm_valid_decisions=1,
        invalid_run_policy="drop",
        experiment_dataset="agent_ecology3_emergence",
        experiment_project="agent_ecology3",
        experiment_phase="phase1",
        llm_client_repo="/home/brian/projects/llm_client",
        model=None,
        subscription_estimated_cost_multiplier=None,
        loop_llm_cooldown=0.0,
        loop_prompt_template=None,
        min_llm_attempt_rate=None,
        min_llm_valid_decision_rate=None,
        gate_policy=None,
    )

    record = _run_condition(args, scenario_id="demo", condition="baseline")
    assert record["exit_code"] == 0
    assert captured_cmd[0] == sys.executable
    assert captured_cmd[1] == "-u"
    assert captured_cmd[2:5] == ["-m", "agent_ecology3.analysis.scarcity_matrix", "--config"]
