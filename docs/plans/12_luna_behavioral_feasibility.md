# Plan #12: Luna Behavioral Feasibility Probe

**Status:** Preregistered and authorized — execution preflight
**Type:** evaluation design
**Priority:** High
**Blocked By:** Plan #11 complete
**Blocks:** Any replicated Luna cognition comparison

## Goal

Implement and execute Evaluation 12's one-pair, two-principal feasibility probe
without reviving or rerunning Evaluation 07.

## Current increment

Freeze the 32-call design, provider-free validator, and exact matched-cell
acknowledgements. The user authorized the exact ceiling on 2026-08-13; dispatch
still requires a clean pushed implementation revision and passing preflight.

## Files

- `config/evaluations/12_luna_behavioral_feasibility.json`
- `src/agent_ecology3/analysis/behavioral_feasibility.py`
- `scripts/run_recoverable_evaluation.py`
- `tests/test_recoverable_poc.py`
- `tests/test_behavioral_feasibility.py`
- `docs/evaluations/12_luna_behavioral_feasibility.md`
- `docs/plans/12_luna_behavioral_feasibility.md`
- `docs/plans/CLAUDE.md`

## Acceptance

- [x] Canonical design passes with `provider_calls=0` and exact ceiling 32.
- [x] Mutations of call ceiling, retries, budget, principal count, and claim
      scope fail closed.
- [x] Focused tests, mypy, and Ruff pass.
- [x] No Luna call occurs and execution remains separately authorized.
- [x] Prescribed/minimal acknowledgements freeze cognition mode, two
      principals, seed `24120`, budget `0.033192`, and 16 attempts per cell.
