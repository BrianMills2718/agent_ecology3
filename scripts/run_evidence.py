#!/usr/bin/env python3
"""Readout and publishable bundle for a resident CodeFlowBench run.

``report`` computes a run's numbers from the kernel's own events and the
receipt (which carries each agent's shell-command count read from its Codex
history): tasks solved, failed submissions by cause, royalties and their
authors, and how often an already-solved helper was called versus rewritten.

``bundle`` writes ``<run_id>.tar.gz`` for the public repo. It drops the
agents' Codex folders, withholds every free-text field that could carry
CodeFlowBench task, solution or test text, reduces checker reasons to the
error type, and refuses to write if any task sentence or hidden test input
from the bank still appears.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import sys
import tarfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from agent_ecology3.world.mint import _FENCE

WITHHELD = "[withheld: CodeFlowBench-derived text]"
FREE_TEXT_KEYS = frozenset(
    {"content", "prompt", "code", "note", "test", "reasoning", "message", "data", "result", "intent"}
)
_ERROR_TYPE = re.compile(r"\(([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|Exit|Interrupt))\b")
_ARG_COUNT = re.compile(
    r"positional argument|required positional|takes \d+ |takes from \d+|unexpected keyword argument"
)


def failure_cause(reason: str) -> str:
    """Classify a checker reason by its error type (Python's own error text)."""
    if _ARG_COUNT.search(reason):
        return "wrong argument count"
    match = _ERROR_TYPE.search(reason)
    if match is None:
        return "other"
    kind = match.group(1)
    if kind == "AssertionError":
        return "wrong answer"
    if kind == "TypeError":
        return "wrong argument type"
    return kind


def _redact_reason(reason: str, passed: bool) -> str:
    task = reason.split(":", 1)[0]
    if passed:
        return f"{task}: passed all hidden tests"
    match = _ERROR_TYPE.search(reason)
    return f"{task}: failed hidden tests ({match.group(1) if match else 'other'}; details withheld)"


def redact(value: Any, *, passed: bool | None = None) -> Any:
    if isinstance(value, dict):
        passed_here = value.get("passed") if isinstance(value.get("passed"), bool) else passed
        out: dict[str, Any] = {}
        for key, item in value.items():
            if key in FREE_TEXT_KEYS and isinstance(item, str):
                out[key] = WITHHELD
            elif key == "reason" and isinstance(item, str):
                out[key] = _redact_reason(item, bool(passed_here))
            else:
                out[key] = redact(item, passed=passed_here)
        return out
    if isinstance(value, list):
        return [redact(item, passed=passed) for item in value]
    return value


def _events(run_dir: Path) -> list[dict[str, Any]]:
    paths = sorted(run_dir.glob("logs/*/events.jsonl"))
    if not paths:
        raise SystemExit(f"no events.jsonl under {run_dir}/logs")
    return [json.loads(line) for line in paths[0].read_text().splitlines() if line.strip()]


def _bank(path: Path) -> dict[str, dict[str, Any]]:
    return {row["task_id"]: row for row in map(json.loads, path.read_text().splitlines()) if row}


def _parse(code: str) -> ast.AST | None:
    fenced = _FENCE.match(code)
    try:
        return ast.parse(fenced.group("body") if fenced else code)
    except SyntaxError:
        return None


def _defines(code: str, name: str) -> bool:
    tree = _parse(code)
    if tree is None:
        return False
    return any(isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name == name for n in ast.walk(tree))


def _calls(code: str, name: str) -> bool:
    tree = _parse(code)
    if tree is None:
        return False
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name for n in ast.walk(tree))


def report(run_dir: Path, bank_path: Path) -> dict[str, Any]:
    events = _events(run_dir)
    receipt = json.loads((run_dir / "run_receipt.json").read_text())
    bank = _bank(bank_path)
    artifacts = {a["id"]: a for a in receipt["world_state"]["artifacts"]}
    scored = [e for e in events if e.get("event_type") == "task_bounty_scored"]
    royalties = [e for e in events if e.get("event_type") == "royalty_paid"]

    solved_at: dict[str, int] = {}
    for event in scored:
        if event["passed"] and event.get("first_claim"):
            solved_at.setdefault(event["task_id"], event["sequence"])

    called = rewritten = 0
    for event in scored:
        if not (event["passed"] and event.get("first_claim")):
            continue
        task = bank.get(event["task_id"], {})
        code = str(artifacts.get(event["artifact_id"], {}).get("content", ""))
        for dep in task.get("requires", []):
            if dep not in solved_at or solved_at[dep] > event["sequence"]:
                continue
            helper = bank[dep]["entry_point"]
            if _defines(code, helper):
                rewritten += 1
            elif _calls(code, helper):
                called += 1

    agents = receipt.get("agents", {})
    turns_recorded = sum(int(a.get("turns", 0)) for a in agents.values())
    return {
        "run_id": receipt["world_state"].get("run_id"),
        "lifecycle_state": receipt.get("recovery", {}).get("lifecycle_state"),
        "agent_turns_recorded": turns_recorded,
        "sessions_per_agent": {k: len(set(a.get("session_ids", []))) for k, a in agents.items()},
        "tasks": len(bank),
        "tasks_solved": len(solved_at),
        "submissions": len(scored),
        "failed_submissions": sum(1 for e in scored if not e["passed"]),
        "unpaid_passes": sum(1 for e in scored if e["passed"] and not e.get("first_claim")),
        "failure_causes": dict(Counter(failure_cause(e["reason"]) for e in scored if not e["passed"]).most_common()),
        "shell_commands_from_history": {k: a.get("shell_commands_from_history") for k, a in agents.items()},
        "royalties_paid": len(royalties),
        "royalty_scrip": sum(int(e["amount"]) for e in royalties),
        # royalty_paid: principal_id is the author who receives the royalty.
        "royalties_by_author": dict(Counter(e["principal_id"] for e in royalties).most_common()),
        "solved_helper_called": called,
        "solved_helper_rewritten": rewritten,
        "final_scrip": {k: v for k, v in sorted(receipt["world_state"].get("balances", {}).items())},
    }


def _leaks(blob: str, bank: dict[str, dict[str, Any]]) -> list[str]:
    found: list[str] = []
    for task_id, row in bank.items():
        statement = row["prompt"].split("\n\n", 1)[-1]
        for sentence in re.split(r"(?<=[.!?])\s+", statement):
            sentence = sentence.strip()
            if len(sentence) >= 40 and (sentence in blob or json.dumps(sentence)[1:-1] in blob):
                found.append(f"{task_id}: statement text")
        cases = re.search(r"_CASES = (\[.*\])", row.get("test", ""))
        for inp, _out in json.loads(cases.group(1)) if cases else []:
            if len(inp) >= 6 and (inp in blob or json.dumps(inp)[1:-1] in blob):
                found.append(f"{task_id}: hidden test input")
    return sorted(set(found))


def bundle(run_dir: Path, bank_path: Path, out: Path) -> int:
    run_id = run_dir.name
    files: dict[str, bytes] = {}
    for path in sorted(run_dir.rglob("*")):
        rel = path.relative_to(run_dir)
        if path.is_symlink() or not path.is_file() or (rel.parts and rel.parts[0] == "agents"):
            continue
        if path.suffix == ".jsonl":
            text = "".join(json.dumps(redact(json.loads(l))) + "\n" for l in path.read_text().splitlines() if l.strip())
        elif path.suffix == ".json":
            text = json.dumps(redact(json.loads(path.read_text())), indent=1)
        else:
            raise SystemExit(f"refusing to bundle unredactable file {rel}")
        files[f"{run_id}/{rel}"] = text.encode()
    leaks = _leaks("\n".join(b.decode() for b in files.values()), _bank(bank_path))
    if leaks:
        print("REFUSED: bank text remains in the bundle:", *leaks[:10], sep="\n  ", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out, "w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    print(f"wrote {out} ({out.stat().st_size} bytes, {len(files)} files, 0 bank leaks)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["report", "bundle"])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="bundle path (bundle only)")
    args = parser.parse_args(argv)
    if args.command == "report":
        print(json.dumps(report(args.run_dir, args.bank), indent=1))
        return 0
    if args.out is None:
        parser.error("bundle needs --out")
    return bundle(args.run_dir, args.bank, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
