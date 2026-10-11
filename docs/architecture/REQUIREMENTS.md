---
description: What the AE3 workbench must do for its operator, each requirement with the observable result that shows it met and the one that would show it broken
---

# Agent Ecology 3: requirements

Each requirement names what must hold, how success is observed and what would
disprove it. The rules that enforce them, with owner files and tests, are in
[trace.yaml](../model/trace.yaml); the model they describe is
[ODD.md](../model/ODD.md); the goal they serve is [GOAL.md](GOAL.md).

## REQ-LAUNCH-BOUNDED-RUN

Brian launches a bounded resident ecology (agents, turns, call budget, task set,
trading on or off) from one command or the dashboard, without editing code.

Success: `scripts/run_resident_ecology.py` with config and CLI overrides runs to
its turn or budget limit and writes `events.jsonl` and `run_receipt.json`.

Disproof: a scenario change that the roadmap lists as configurable needs a
source edit, or a run exceeds its declared turn or budget bound.

## REQ-REOPEN-READ-ONLY

A completed run reopens in the dashboard read-only from its preserved evidence,
with zero model calls.

Success: `tests/test_recoverable_poc.py::test_dashboard_reopens_completed_pair_read_only`
passes, and reopening a committed evidence bundle makes no model call.

Disproof: reopening a run calls a model, mutates its files, or shows a
comparison condition that was never run.

## REQ-FAIL-LOUD

An authentic run stops and is recorded invalid on any model, transport, schema
or checker failure; nothing is substituted for a failed decision or check.

Success: `tests/test_plan24_task_bounty.py::test_checker_infrastructure_failure_fails_loud`
passes, and a resident failure raises `ResidentRunError` and ends the run.

Disproof: a run with a failed model call or checker failure finishes and is
reported valid, or a default action or score fills the gap.

## REQ-OUTSIDE-CHECKER-PAYS

New scrip enters the economy only from the outside checker, and only the first
passing submission per task is paid.

Success: `tests/test_plan24_task_bounty.py::test_only_first_passing_submission_is_paid_and_bids_are_refunded`
passes, and every `task_bounty_scored` event with minted scrip is the first pass
for its task.

Disproof: scrip is minted without a passing hidden-test score, or two passes on
one task are both paid.

## REQ-TRADING-SWITCH

One setting switches trading between agents on or off, so the same agents can
run as a trading economy and as a solo baseline.

Success: `tests/test_plan24_task_bounty.py::test_solo_closes_cross_principal_reads_and_transfers`
and `::test_trading_mode_charges_cross_reads` pass.

Disproof: with trading off, any scrip moves between two principals by a read or
transfer.

## REQ-ROYALTY-ON-REAL-REUSE

A helper's author earns a royalty only when another agent's passing solution
actually calls that helper.

Success: the three royalty tests in `tests/test_compounding_tasks.py` pass
(paid on a call; unpaid on redefinition; unpaid without a call).

Disproof: a `royalty_paid` event appears for a solution that never calls the
helper or defines it itself.

## REQ-MODEL-MATCHES-CODE

The declared model (`docs/model/ae3_model.yaml`, described in ODD.md) lists
exactly the events the code writes, with the same emitters and fields.

Success: `tests/test_model_declaration.py` passes in `make check`.

Disproof: an event appears in a run's `events.jsonl` that the model does not
declare, or a declared event cannot be emitted by any code path.

## REQ-ACTION-LIMIT

Each resident agent is held to its per-turn action limit, so scarcity of
actions is real.

Success: `tests/test_resident_agents.py::test_endpoint_enforces_actions_per_turn`
passes, and over-limit calls appear as `turn_action_limit` refusals.

Disproof: an agent completes more than `actions_per_turn` actions in one turn.
