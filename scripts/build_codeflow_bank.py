"""Build a local task bank of CodeFlowBench helper functions that depend on each other.

CodeFlowBench (MIT, https://github.com/Rise-1210/codeflow) splits Codeforces
problems into helper functions with declared dependencies and literal
input/output tests. Each kept helper becomes one bountied task whose
``requires`` lists the helpers it calls, so later tasks build on earlier ones.

The bank is written outside the repository (default ``~/.cache/agent_ecology3``)
because redistribution terms for the Codeforces-derived text are unverified;
only this builder is committed.

A helper is kept only when it has at least two tests whose inputs and outputs
are Python literals. (The dataset's "solutions" are tokenized editorial text,
often C++, so they cannot validate the tests.)

Example:
    uv run python scripts/build_codeflow_bank.py --agents 8 --problems 16 --seed 25101
"""

from __future__ import annotations

import argparse
import ast
import json
import random
import sys
import urllib.request
from pathlib import Path
from typing import Any

DATASET_URL = "https://raw.githubusercontent.com/Rise-1210/codeflow/main/data/codeflowbench_comp_test.json"
CACHE = Path.home() / ".cache" / "agent_ecology3"
SKIP_NAMES = {"solve", "main"}


def _literal(text: str) -> tuple[bool, Any]:
    try:
        return True, ast.literal_eval(text)
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return False, None


def _cases(helper: dict[str, Any]) -> list[tuple[str, str]]:
    kept: list[tuple[str, str]] = []
    for case in helper.get("test_code") or []:
        if not isinstance(case, dict):
            continue
        ok_in, args = _literal(str(case.get("input", "")))
        ok_out, _ = _literal(str(case.get("output", "")))
        if ok_in and ok_out and isinstance(args, tuple):
            kept.append((str(case["input"]), str(case["output"])))
    return kept


def check_code(cases: list[tuple[str, str]]) -> str:
    """Hidden test: call the candidate on each literal input, compare literal outputs."""
    return (
        "import ast as _ast\n"
        f"_CASES = {json.dumps(cases)}\n"
        "def check(candidate):\n"
        "    for _inp, _out in _CASES:\n"
        "        _args = _ast.literal_eval(_inp)\n"
        "        assert candidate(*_args) == _ast.literal_eval(_out), (_inp, _out)\n"
    )


def build(problems: list[dict[str, Any]], *, agents: int, count: int, seed: int) -> list[dict[str, Any]]:
    candidates = []
    for problem in problems:
        helpers = [h for h in problem.get("subproblems") or [] if h.get("name") not in SKIP_NAMES]
        if len(helpers) >= 3 and any(h.get("dependencies") for h in helpers):
            candidates.append(problem)
    random.Random(seed).shuffle(candidates)
    rows: list[dict[str, Any]] = []
    owner_index = 0
    for problem in candidates:
        if len({r["problem"] for r in rows}) >= count:
            break
        pid = str(problem["problem-id"])
        kept: dict[str, dict[str, Any]] = {}
        for helper in problem["subproblems"]:
            name = str(helper.get("name"))
            if name in SKIP_NAMES:
                continue
            cases = _cases(helper)
            if len(cases) < 2:
                continue
            kept[name] = {"helper": helper, "test": check_code(cases)}
        if len(kept) < 3 or not any(
            dep in kept for k in kept.values() for dep in k["helper"].get("dependencies") or []
        ):
            continue
        for name, item in kept.items():
            helper = item["helper"]
            requires = [f"CF/{pid}/{dep}" for dep in helper.get("dependencies") or [] if dep in kept]
            rows.append({
                "task_id": f"CF/{pid}/{name}",
                "problem": pid,
                "owner": f"alpha_{owner_index % agents + 1}",
                "entry_point": name,
                "prompt": f"Write the Python function `{name}`.\n\n{helper.get('statement', '').strip()}",
                "test": item["test"],
                "requires": requires,
            })
            owner_index += 1
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agents", type=int, default=8)
    parser.add_argument("--problems", type=int, default=16)
    parser.add_argument("--seed", type=int, default=25101)
    parser.add_argument("--dataset", type=Path, default=CACHE / "codeflowbench_comp_test.json")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    if not args.dataset.is_file():
        args.dataset.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(DATASET_URL, args.dataset)
    problems = json.loads(args.dataset.read_text(encoding="utf-8"))
    rows = build(problems, agents=args.agents, count=args.problems, seed=args.seed)
    out = args.out or CACHE / f"codeflow_bank_a{args.agents}_p{args.problems}_s{args.seed}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    owners = sorted({r["owner"] for r in rows})
    with_deps = sum(1 for r in rows if r["requires"])
    print(json.dumps({"bank": str(out), "tasks": len(rows), "problems": len({r["problem"] for r in rows}),
                      "tasks_with_dependencies": with_deps, "owners": owners}))
    if set(owners) != {f"alpha_{n}" for n in range(1, args.agents + 1)}:
        print("ERROR: not every agent owns a task; raise --problems", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
