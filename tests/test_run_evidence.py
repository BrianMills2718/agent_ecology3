"""Run readout and redacted bundle (scripts/run_evidence.py); no model calls."""

from __future__ import annotations

import importlib.util
import json
import tarfile
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _module() -> Any:
    spec = importlib.util.spec_from_file_location("run_evidence", SCRIPTS / "run_evidence.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STATEMENT = "Calculate the sum of the digits of a given integer x for the gcd step."
BANK_ROWS = [
    {"task_id": "CF/X/digits", "entry_point": "digits", "requires": [],
     "prompt": "Write the Python function `digits`.\n\n" + STATEMENT,
     "test": '_CASES = [["(123456,)", "21"]]\n'},
    {"task_id": "CF/X/gsum", "entry_point": "gsum", "requires": ["CF/X/digits"],
     "prompt": "Write the Python function `gsum`.\n\nCompute gcd of x and its digit sum for the answer.",
     "test": '_CASES = [["(987654,)", "3"]]\n'},
]


def _run(tmp_path: Path, reuse_code: str) -> tuple[Path, Path]:
    bank = tmp_path / "bank.jsonl"
    bank.write_text("".join(json.dumps(r) + "\n" for r in BANK_ROWS))
    run = tmp_path / "run_x"
    (run / "logs" / "run_x").mkdir(parents=True)
    (run / "agents" / "alpha_1" / "codex_home").mkdir(parents=True)
    (run / "agents" / "alpha_1" / "codex_home" / "auth.json").write_text('{"token": "secret"}')
    events = [
        {"event_type": "task_bounty_scored", "sequence": 1, "principal_id": "alpha_1", "artifact_id": "a1",
         "task_id": "CF/X/digits", "passed": True, "first_claim": True, "reason": "CF/X/digits: passed all hidden tests"},
        {"event_type": "task_bounty_scored", "sequence": 2, "principal_id": "alpha_2", "artifact_id": "b0",
         "task_id": "CF/X/gsum", "passed": False, "first_claim": False,
         "reason": "CF/X/gsum: failed hidden tests (AssertionError: ('(987654,)', '3'))"},
        {"event_type": "task_bounty_scored", "sequence": 3, "principal_id": "alpha_2", "artifact_id": "b1",
         "task_id": "CF/X/gsum", "passed": False, "first_claim": False,
         "reason": "CF/X/gsum: failed hidden tests (TypeError: gsum() takes 1 positional argument but 2 were given)"},
        {"event_type": "task_bounty_scored", "sequence": 4, "principal_id": "alpha_2", "artifact_id": "b2",
         "task_id": "CF/X/gsum", "passed": True, "first_claim": True, "reason": "CF/X/gsum: passed all hidden tests"},
        {"event_type": "royalty_paid", "sequence": 5, "principal_id": "alpha_1", "solver": "alpha_2", "amount": 3},
        {"event_type": "resident_turn", "note": STATEMENT},
    ]
    (run / "logs" / "run_x" / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    receipt = {"recovery": {"lifecycle_state": "completed"},
               "agents": {"alpha_1": {"turns": 2, "session_ids": ["s", "s"], "shell_commands_from_history": 4}},
               "world_state": {"run_id": "run_x", "balances": {},
                               "artifacts": [{"id": "b2", "content": "```python\n" + reuse_code + "```"}]}}
    (run / "run_receipt.json").write_text(json.dumps(receipt))
    return run, bank


def test_report_counts_from_events_and_receipt(tmp_path: Path) -> None:
    run, bank = _run(tmp_path, "from math import gcd\ndef gsum(x):\n    return gcd(x, digits(x))\n")
    r = _module().report(run, bank)
    assert r["tasks_solved"] == 2 and r["failed_submissions"] == 2
    assert r["failure_causes"] == {"wrong answer": 1, "wrong argument count": 1}
    assert r["royalties_by_author"] == {"alpha_1": 1}
    assert (r["solved_helper_called"], r["solved_helper_rewritten"]) == (1, 0)
    assert r["shell_commands_from_history"] == {"alpha_1": 4} and r["agent_turns_recorded"] == 2


def test_report_counts_a_rewritten_helper(tmp_path: Path) -> None:
    run, bank = _run(tmp_path, "def digits(x):\n    return 0\ndef gsum(x):\n    return digits(x)\n")
    r = _module().report(run, bank)
    assert (r["solved_helper_called"], r["solved_helper_rewritten"]) == (0, 1)


def test_bundle_withholds_task_text_and_test_cases_and_codex_home(tmp_path: Path) -> None:
    run, bank = _run(tmp_path, "def gsum(x):\n    return x\n")
    out = tmp_path / "run_x.tar.gz"
    assert _module().bundle(run, bank, out) == 0
    with tarfile.open(out) as tar:
        names = tar.getnames()
        blob = "".join(tar.extractfile(n).read().decode() for n in names)  # type: ignore[union-attr]
    assert not any("agents" in n for n in names)
    assert "secret" not in blob and STATEMENT not in blob and "987654" not in blob
    assert "failed hidden tests (AssertionError; details withheld)" in blob


def test_bundle_refuses_when_bank_text_survives(tmp_path: Path) -> None:
    run, bank = _run(tmp_path, "def gsum(x):\n    return x\n")
    (run / "logs" / "run_x" / "events.jsonl").write_text(json.dumps({"event_type": "x", "summary": STATEMENT}) + "\n")
    assert _module().bundle(run, bank, tmp_path / "out.tar.gz") == 1
    assert not (tmp_path / "out.tar.gz").exists()
