# Plan #11: Luna Scarcity Calibration

**Status:** Provider-free projection complete — authentic probe gated
**Type:** evaluation design and instrument
**Priority:** High
**Blocked By:** Plan #10 complete
**Blocks:** Any new-number Luna behavioral comparison

---

## Gap

**Current:** Plan 10 proves recoverable Luna execution, but not reliability or
scarcity. Evaluation 07 used `0.25` starting LLM budget per principal and ended
without enough scarcity-binding runs to support its behavioral comparison.

**Target:** Derive a small, inspectable set of candidate LLM budgets from
retained Luna settlement charges, then separately authorize one authentic
calibration cell that can show whether scarcity actually binds within its
frozen horizon.

**Why:** A new behavioral comparison is wasteful and invalid if agents can
finish the attempt horizon without encountering the intended constraint.

## References Reviewed

- `docs/plans/10_luna_medium_recovery_gate.md` — accepted route, recovery, and non-claims
- `docs/evaluations/evidence/plan10_luna_recovery_gate/dashboard_poc.json` — retained Luna charges
- `config/config.behavioral_comparison_07.yaml` — prior `0.25` per-principal setting
- `src/agent_ecology3/world/world.py` — reservation and subscription settlement semantics
- `src/agent_ecology3/analysis/behavioral_comparison.py` — scarcity receipt classification

## Bounded Design

The provider-free readout uses the maximum retained Plan 10 internal estimated
charge as an observed reference. It projects how many attempts the old budget
could fund and derives one-attempt, midpoint, and full-horizon settings. These
are calibration candidates, not future cost bounds or behavioral evidence.

The first authentic probe, if separately authorized, uses only the midpoint
candidate through Plan 10's recoverable runner. It passes only if a retained
`insufficient_budget` receipt appears before the frozen horizon while the
dashboard preserves the concrete action and budget trajectory. It is
inconclusive if another gate prevents interpretation and disproved if the
horizon completes without budget scarcity.

No prompt comparison, reliability claim, behavioral-effect claim, retry,
fallback, MCP path, or Evaluation 07 mutation is in this increment.

## Files Affected

- `src/agent_ecology3/analysis/scarcity_calibration.py` (create)
- `tests/test_scarcity_calibration.py` (create)
- `docs/evaluations/evidence/11_luna_scarcity_calibration/provider_free_projection.json` (create)
- `docs/plans/11_luna_scarcity_calibration.md` (create)
- `docs/plans/CLAUDE.md` (modify)

## Required Tests

| Test | Evidence |
| --- | --- |
| Candidate projection | Uses the largest retained positive charge and exact attempt capacities |
| Invalid receipt | Missing or non-positive settlement evidence fails loud |
| Invalid horizon | A non-calibrating horizon is rejected |
| CLI receipt path | Durable JSON readout reproduces from retained Plan 10 evidence |

## Acceptance Criteria

- [x] Provider-free readout reproduces from canonical Plan 10 evidence.
- [x] The old `0.25` setting is classified only as a non-binding projection.
- [x] Candidate settings retain their exact derivation and non-claims.
- [x] Focused tests, type checking, and lint pass.
- [x] No provider call occurs and authentic execution remains separately gated.

## Failure and Reset Boundary

Malformed or absent retained charges stop before producing candidates. A later
authentic cell is immutable evidence for its exact setting: provider or custody
ambiguity stops without retry, and a non-budget failure is inconclusive rather
than evidence that scarcity did or did not bind.
