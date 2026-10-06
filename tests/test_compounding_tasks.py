"""Compounding tasks: dependency linking in the checker, royalties, bank builder."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from agent_ecology3.config import AppConfig
from agent_ecology3.world import World

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _builder() -> Any:
    spec = importlib.util.spec_from_file_location("build_codeflow_bank", SCRIPTS / "build_codeflow_bank.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bank(tmp_path: Path) -> Path:
    b = _builder()
    rows = [
        {"task_id": "CF/X/digits", "owner": "alpha_1", "entry_point": "digits", "prompt": "sum digits",
         "test": b.check_code([("(11,)", "2"), ("(75,)", "12")]), "requires": []},
        {"task_id": "CF/X/gsum", "owner": "alpha_2", "entry_point": "gsum", "prompt": "gcd of x and digits",
         "test": b.check_code([("(12,)", "3"), ("(11,)", "1")]), "requires": ["CF/X/digits"]},
    ]
    path = tmp_path / "bank.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def _world(tmp_path: Path) -> World:
    cfg = AppConfig()
    cfg.principals.count = 2
    cfg.llm.enable_bootstrap_loop_llm = False
    cfg.dashboard.enabled = False
    cfg.logging.logs_dir = str(tmp_path / "logs")
    cfg.mint.mode = "task_bounty"
    cfg.mint.task_bank_path = str(_bank(tmp_path))
    cfg.mint.royalty_scrip = 3
    return World(AppConfig.model_validate(cfg.model_dump()), run_id="compounding")


DIGITS = "def digits(x):\n    return sum(int(c) for c in str(x))\n"
GSUM_REUSING = "from math import gcd\ndef gsum(x):\n    return gcd(x, digits(x))\n"
GSUM_OWN = DIGITS + GSUM_REUSING


def _submit(world: World, who: str, artifact_id: str, task: str, code: str) -> dict[str, Any]:
    assert world.execute_action_data(who, {"action_type": "write_artifact", "artifact_id": artifact_id,
                                           "artifact_type": f"solution:{task}", "content": code}).success
    result = world.execute_action_data(who, {"action_type": "submit_to_mint", "artifact_id": artifact_id, "bid": 1})
    assert result.success, result.message
    return dict(result.data)


def _royalties(world: World) -> list[dict[str, Any]]:
    return [e for e in world.logger.read_recent(500) if e.get("event_type") == "royalty_paid"]


def test_unsolved_dependency_is_not_linked(tmp_path: Path) -> None:
    world = _world(tmp_path)
    outcome = _submit(world, "alpha_2", "alpha_2_g", "CF/X/gsum", GSUM_REUSING)
    assert outcome["passed"] is False and "NameError" in outcome["reason"]
    assert _royalties(world) == []


def test_solved_dependency_is_linked_and_its_author_earns_a_royalty(tmp_path: Path) -> None:
    world = _world(tmp_path)
    assert _submit(world, "alpha_1", "alpha_1_d", "CF/X/digits", DIGITS)["first_claim"] is True
    before = world.ledger.get_scrip("alpha_1")
    outcome = _submit(world, "alpha_2", "alpha_2_g", "CF/X/gsum", GSUM_REUSING)
    assert outcome["passed"] is True and outcome["first_claim"] is True
    assert world.ledger.get_scrip("alpha_1") == before + 3
    royalties = _royalties(world)
    assert len(royalties) == 1
    assert royalties[0]["principal_id"] == "alpha_1" and royalties[0]["solver"] == "alpha_2"
    assert royalties[0]["dependency_task_id"] == "CF/X/digits" and royalties[0]["amount"] == 3


def test_no_royalty_when_the_solver_defines_the_helper_itself(tmp_path: Path) -> None:
    world = _world(tmp_path)
    _submit(world, "alpha_1", "alpha_1_d", "CF/X/digits", DIGITS)
    outcome = _submit(world, "alpha_2", "alpha_2_g", "CF/X/gsum", GSUM_OWN)
    assert outcome["passed"] is True
    assert _royalties(world) == []


def test_builder_keeps_helper_chains_and_spreads_owners() -> None:
    b = _builder()
    def helper(name: str, deps: list[str]) -> dict[str, Any]:
        return {"name": name, "statement": f"do {name}", "dependencies": deps,
                "test_code": [{"input": "(1,)", "output": "1"}, {"input": "(2,)", "output": "2"}]}
    problems = [{"problem-id": f"P{n}", "subproblems": [helper("a", []), helper("b", ["a"]), helper("c", ["b"]),
                                                         helper("solve", ["c"])]} for n in range(3)]
    rows = b.build(problems, agents=3, count=3, seed=1)
    assert len(rows) == 9 and not any(r["entry_point"] == "solve" for r in rows)
    by_id = {r["task_id"]: r for r in rows}
    assert by_id["CF/P0/b"]["requires"] == ["CF/P0/a"]
    assert {r["owner"] for r in rows} == {"alpha_1", "alpha_2", "alpha_3"}
    assert by_id["CF/P0/a"]["owner"] != by_id["CF/P0/b"]["owner"]
