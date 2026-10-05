"""Plan 24 M2: outside-scored task bounty, trading switch, and review readout."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agent_ecology3.config import AppConfig, LLMConfig
from agent_ecology3.dashboard.server import create_app
from agent_ecology3.world import World
from agent_ecology3.world.mint import (
    MintScoringError,
    TaskCheckerScorer,
    load_task_bank,
)

BANK = Path(__file__).resolve().parents[1] / "config" / "tasks" / "humaneval_plan24_v1.jsonl"
CONCAT_OK = (
    "from typing import List\n\n"
    "def concatenate(strings: List[str]) -> str:\n"
    "    return ''.join(strings)\n"
)
CONCAT_WRONG = "def concatenate(strings):\n    return ' '.join(strings)\n"


def _config(tmp_path: Path, *, trading: bool = True) -> AppConfig:
    cfg = AppConfig()
    cfg.principals.count = 2
    cfg.principals.starting_scrip = 100
    cfg.llm.enable_bootstrap_loop_llm = False
    cfg.dashboard.enabled = False
    cfg.logging.logs_dir = str(tmp_path / "logs")
    cfg.logging.recent_event_limit = 1000
    cfg.mint.enabled = True
    cfg.mint.mode = "task_bounty"
    cfg.mint.task_bank_path = str(BANK)
    cfg.economy.cross_principal_trading = trading
    return AppConfig.model_validate(cfg.model_dump())


def _write(world: World, principal: str, artifact_id: str, artifact_type: str, content: str, price: int = 0) -> None:
    result = world.execute_action_data(
        principal,
        {
            "action_type": "write_artifact",
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "content": content,
            "read_price": price,
        },
    )
    assert result.success, result.message


def test_task_bank_is_frozen_and_split_between_two_principals() -> None:
    tasks = load_task_bank(BANK)
    assert sorted(tasks) == sorted(
        f"HumanEval/{n}" for n in (28, 34, 55, 56, 81, 85, 98, 137)
    )
    owners = [task.owner for task in tasks.values()]
    assert owners.count("alpha_1") == 4 and owners.count("alpha_2") == 4
    assert all("def check(" in task.test for task in tasks.values())


def test_checker_passes_fails_and_rejects_unknown_tasks() -> None:
    scorer = TaskCheckerScorer(load_task_bank(BANK), timeout_seconds=10)
    assert scorer.score_artifact("a", "solution:HumanEval/28", CONCAT_OK, "")[0] == 100
    fenced = "```python\n" + CONCAT_OK + "```"
    assert scorer.score_artifact("a", "solution:HumanEval/28", fenced, "")[0] == 100
    score, reason = scorer.score_artifact("a", "solution:HumanEval/28", CONCAT_WRONG, "")
    assert score == 0 and "failed hidden tests" in reason
    score, reason = scorer.score_artifact("a", "note", CONCAT_OK, "")
    assert score == 0 and "names no task" in reason
    score, reason = scorer.score_artifact("a", "solution:HumanEval/0", CONCAT_OK, "")
    assert score == 0 and "names no task" in reason
    assert scorer.score_artifact("a", "solution:humaneval/28", CONCAT_OK, "")[0] == 100


def test_checker_times_out_as_a_failed_solution() -> None:
    scorer = TaskCheckerScorer(load_task_bank(BANK), timeout_seconds=1)
    loop = "def concatenate(strings):\n    while True:\n        pass\n"
    score, reason = scorer.score_artifact("a", "solution:HumanEval/28", loop, "")
    assert score == 0 and "timed out" in reason


def test_checker_infrastructure_failure_fails_loud(monkeypatch: Any) -> None:
    scorer = TaskCheckerScorer(load_task_bank(BANK), timeout_seconds=10)

    def broken(*_: Any, **__: Any) -> Any:
        raise OSError("no interpreter")

    monkeypatch.setattr(subprocess, "run", broken)
    with pytest.raises(MintScoringError, match="no interpreter"):
        scorer.score_artifact("a", "solution:HumanEval/28", CONCAT_OK, "")


def test_only_first_passing_submission_is_paid_and_bids_are_refunded(tmp_path: Path) -> None:
    world = World(_config(tmp_path), run_id="plan24_bounty")
    _write(world, "alpha_1", "alpha_1_sol", "solution:HumanEval/28", CONCAT_OK)
    _write(world, "alpha_2", "alpha_2_sol", "solution:HumanEval/28", CONCAT_OK)
    _write(world, "alpha_2", "alpha_2_bad", "solution:HumanEval/28", CONCAT_WRONG)

    first = world.execute_action_data(
        "alpha_1", {"action_type": "submit_to_mint", "artifact_id": "alpha_1_sol", "bid": 1}
    )
    assert first.success and first.data["first_claim"] is True and first.data["scrip_minted"] == 10
    second = world.execute_action_data(
        "alpha_2", {"action_type": "submit_to_mint", "artifact_id": "alpha_2_sol", "bid": 1}
    )
    assert second.success and second.data["scrip_minted"] == 0
    assert "already claimed by alpha_1" in second.data["reason"]
    failed = world.execute_action_data(
        "alpha_2", {"action_type": "submit_to_mint", "artifact_id": "alpha_2_bad", "bid": 1}
    )
    assert failed.success and failed.data["passed"] is False
    assert world.ledger.get_scrip("alpha_1") == 110
    assert world.ledger.get_scrip("alpha_2") == 100


def test_solo_closes_cross_principal_reads_and_transfers(tmp_path: Path) -> None:
    world = World(_config(tmp_path, trading=False), run_id="plan24_solo")
    _write(world, "alpha_2", "alpha_2_task", "task_statement", "secret task", price=2)

    read = world.execute_action_data(
        "alpha_1", {"action_type": "read_artifact", "artifact_id": "alpha_2_task"}
    )
    assert not read.success and read.error_code == "trading_disabled"
    transfer = world.execute_action_data(
        "alpha_1", {"action_type": "transfer", "recipient_id": "alpha_2", "amount": 1}
    )
    assert not transfer.success and transfer.error_code == "trading_disabled"
    listing = world.query_handler.execute(
        "artifacts", {"_principal_id": "alpha_1", "readable_only": True}
    )
    assert "alpha_2_task" not in {row["id"] for row in listing["results"]}
    own = world.execute_action_data(
        "alpha_2", {"action_type": "read_artifact", "artifact_id": "alpha_2_task"}
    )
    assert own.success
    assert world.ledger.get_scrip("alpha_1") == 100


def test_trading_mode_charges_cross_reads(tmp_path: Path) -> None:
    world = World(_config(tmp_path, trading=True), run_id="plan24_trading")
    _write(world, "alpha_2", "alpha_2_task", "task_statement", "task", price=2)
    read = world.execute_action_data(
        "alpha_1", {"action_type": "read_artifact", "artifact_id": "alpha_2_task"}
    )
    assert read.success
    assert world.ledger.get_scrip("alpha_1") == 98
    assert world.ledger.get_scrip("alpha_2") == 102


def test_queries_do_not_leak_priced_content(tmp_path: Path) -> None:
    world = World(_config(tmp_path, trading=True), run_id="plan24_leaks")
    _write(world, "alpha_2", "alpha_2_task", "task_statement", "PRICED SECRET", price=2)

    other = world.query_handler.execute(
        "artifact", {"_principal_id": "alpha_1", "artifact_id": "alpha_2_task"}
    )
    assert other["result"]["content"] is None
    assert "read_artifact" in other["result"]["content_withheld"]
    owner = world.query_handler.execute(
        "artifact", {"_principal_id": "alpha_2", "artifact_id": "alpha_2_task"}
    )
    assert owner["result"]["content"] == "PRICED SECRET"
    assert "PRICED SECRET" in json.dumps(world.logger.read_recent(200))
    events = world.query_handler.execute("events", {"limit": 200})
    assert "PRICED SECRET" not in json.dumps(events)


def test_luna_profile_accepts_low_and_medium_only() -> None:
    base = {
        "decision_output_mode": "luna_structured_v1",
        "default_model": "codex/gpt-5.6-luna",
        "codex_transport": "cli",
        "codex_sandbox_mode": "read-only",
        "codex_approval_policy": "never",
        "codex_isolate_home": True,
        "structured_response_model": "LunaLoopDecisionV1",
        "expected_billing_mode": "subscription_included",
        "num_retries": 0,
        "agent_cwd": None,
    }
    for effort in ("low", "medium"):
        assert LLMConfig.model_validate({**base, "reasoning_effort": effort}).reasoning_effort == effort
    for effort in ("high", None):
        with pytest.raises(ValueError, match="reasoning_effort"):
            LLMConfig.model_validate({**base, "reasoning_effort": effort})


def _receipt_dir(tmp_path: Path, condition: str, events: list[dict[str, Any]]) -> Path:
    data_dir = tmp_path / condition
    data_dir.mkdir()
    log_path = data_dir / "events.jsonl"
    log_path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    receipt = {
        "acknowledgement": f"plan24/luna-low/task-bounty/{condition}/v2",
        "model": "codex/gpt-5.6-luna",
        "recovery": {"committed_attempts": 4, "target_attempts": 4, "lifecycle_state": "complete"},
        "world_state": {"balances": {}, "artifact_count": 0, "log_path": str(log_path)},
    }
    (data_dir / "run_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    return data_dir


def _decision(n: int, principal: str, action: str) -> dict[str, Any]:
    return {
        "event_type": "loop_decision",
        "event_number": n,
        "principal_id": principal,
        "decision_action": action,
        "result_success": True,
        "fallback_used": False,
        "decision": {},
    }


def test_review_shows_trading_vs_solo_readout(tmp_path: Path) -> None:
    trading = _receipt_dir(
        tmp_path,
        "trading",
        [
            _decision(1, "alpha_1", "read_artifact"),
            {"event_type": "artifact_read", "event_number": 1, "principal_id": "alpha_1",
             "artifact_id": "alpha_2_task_34", "recipient": "alpha_2", "read_price_paid": 2},
            _decision(2, "alpha_1", "write_artifact"),
            _decision(3, "alpha_1", "submit_to_mint"),
            {"event_type": "task_bounty_scored", "event_number": 3, "principal_id": "alpha_1",
             "artifact_id": "alpha_1_sol_34", "task_id": "HumanEval/34", "passed": True,
             "score": 100, "scrip_minted": 10, "first_claim": True},
            _decision(4, "alpha_2", "query_kernel"),
        ],
    )
    solo = _receipt_dir(
        tmp_path,
        "solo",
        [
            _decision(1, "alpha_1", "write_artifact"),
            _decision(2, "alpha_1", "submit_to_mint"),
            {"event_type": "task_bounty_scored", "event_number": 2, "principal_id": "alpha_1",
             "artifact_id": "alpha_1_sol_28", "task_id": "HumanEval/28", "passed": False,
             "score": 0, "scrip_minted": 0, "first_claim": False},
            _decision(3, "alpha_2", "query_kernel"),
            _decision(4, "alpha_2", "query_kernel"),
        ],
    )
    app = create_app(review_runs={"trading": trading, "solo": solo})
    with TestClient(app) as client:
        assert client.get("/runs").json()["comparison_available"] is True
        summary = client.get("/review-summary").json()
        assert "timelineLeft" in client.get("/").text
    assert summary["pair_kind"] == "trading_vs_solo"
    assert summary["pair_winner"] == "trading"
    assert summary["valid_pair"] is True
    by_id = {run["id"]: run for run in summary["runs"]}
    assert by_id["trading"]["tasks_passed"] == 1
    assert by_id["solo"]["tasks_passed"] == 0
    solved = by_id["trading"]["solved_tasks"][0]
    assert solved["task_id"] == "HumanEval/34"
    assert solved["purchases_before"] == [
        {"artifact_id": "alpha_2_task_34", "seller": "alpha_2", "price": 2}
    ]
    assert by_id["trading"]["calls_by_principal"] == {"alpha_1": 3, "alpha_2": 1}
    assert solved["bought_this_task"] is True
    assert "1 solved task(s) were ones whose statement" in summary["economic_summary"]


def test_loop_normalizer_preserves_agent_authored_artifact_type(tmp_path: Path) -> None:
    """Plan 24 pair 1 was invalidated by the loop lowercasing artifact types."""
    world = World(_config(tmp_path), run_id="plan24_case")
    namespace: dict[str, Any] = {}
    exec(compile(world._default_loop_code("alpha_1", 0), "loop", "exec"), namespace)
    decision, reason = namespace["_normalize_loop_decision"](
        {
            "action_type": "write_artifact",
            "artifact_id": "alpha_1_sol",
            "artifact_type": "solution:HumanEval/28",
            "content": CONCAT_OK,
        },
        {},
    )
    assert reason is None
    assert decision["artifact_type"] == "solution:HumanEval/28"


def test_loop_snapshot_artifact_limit_is_configurable(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    cfg.llm.loop_snapshot_artifact_limit = 80
    world = World(cfg, run_id="plan25_limit")
    assert "limit=80," in world._default_loop_code("alpha_1", 0)


def test_scale_task_bank_assigns_ten_tasks_to_each_of_four_principals() -> None:
    bank = load_task_bank(BANK.with_name("humaneval_scale_v1.jsonl"))
    owners = [task.owner for task in bank.values()]
    assert len(bank) == 40
    assert {owner: owners.count(owner) for owner in set(owners)} == {
        f"alpha_{n}": 10 for n in (1, 2, 3, 4)
    }
    assert not set(bank) & set(load_task_bank(BANK))


def test_interaction_graph_projects_trades_and_solves(tmp_path: Path) -> None:
    from agent_ecology3.dashboard.server import _interaction_graph

    events = [
        {"event_type": "artifact_read", "principal_id": "alpha_1", "recipient": "alpha_2", "read_price_paid": 2},
        {"event_type": "artifact_read", "principal_id": "alpha_1", "recipient": "alpha_2", "read_price_paid": 2},
        {"event_type": "artifact_read", "principal_id": "alpha_2", "recipient": "alpha_2", "read_price_paid": 2},
        {"event_type": "task_bounty_scored", "principal_id": "alpha_1", "task_id": "HumanEval/34", "first_claim": True},
        {"event_type": "task_bounty_scored", "principal_id": "alpha_2", "task_id": "HumanEval/34", "first_claim": False},
    ]
    graph = _interaction_graph(events, {"principals": ["alpha_1", "alpha_2"], "balances": {"alpha_1": {"scrip": 106}}})
    edges = {edge["id"]: edge for edge in graph["edges"]}
    assert edges["bought:alpha_1->alpha_2"]["weight"] == 2
    assert "bought:alpha_2->alpha_2" not in edges
    assert edges["solved:alpha_1->HumanEval/34"]["kind"] == "solved"
    assert edges["attempted:alpha_2->HumanEval/34"]["weight"] == 1
    assert graph["summary"] == {"agents": 2, "paid_reads": 2, "tasks_solved": 1, "failed_attempts": 1}


def test_claimed_task_is_marked_on_its_statement_listing(tmp_path: Path) -> None:
    world = World(_config(tmp_path), run_id="plan25_claimed")
    world.artifacts.write(
        "alpha_2_task_28", "task_statement", "statement", created_by="alpha_2", owner="alpha_2",
        read_price=2, metadata={"plan24_task_id": "HumanEval/28"},
    )
    _write(world, "alpha_1", "alpha_1_sol", "solution:HumanEval/28", CONCAT_OK)
    listing = world.query_handler.execute("artifacts", {"_principal_id": "alpha_1", "readable_only": True})
    assert "bounty_claimed_by" not in {k for row in listing["results"] for k in row}
    world.execute_action_data("alpha_1", {"action_type": "submit_to_mint", "artifact_id": "alpha_1_sol", "bid": 1})
    listing = world.query_handler.execute("artifacts", {"_principal_id": "alpha_1", "readable_only": True})
    row = next(r for r in listing["results"] if r["id"] == "alpha_2_task_28")
    assert row["bounty_claimed_by"] == "alpha_1"
