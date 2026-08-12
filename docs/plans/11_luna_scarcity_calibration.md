# Plan #11: Luna Scarcity Calibration

**Status:** Authentic midpoint probe passed — control design pending
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

## Authentic Midpoint Probe — Frozen Contract

**Claim:** With `0.033192` starting LLM budget, the normal one-principal Luna
loop reaches a proven pre-dispatch `insufficient_budget` boundary before 16
provider dispatches.

**Decision:** A pass makes the midpoint setting eligible for a later
calibration/control design. Completion of 16 dispatches without the boundary
rejects the midpoint. Any other terminal condition is inconclusive.

**Execution:** exact `codex/gpt-5.6-luna`, medium reasoning, CLI,
subscription-included billing, one principal, at most 16 provider dispatches,
zero retries/repair/fallback/MCP, exact accepted shared client, clean pushed AE3
revision, and acknowledgement `plan11/luna-medium/scarcity-midpoint/v1`.

**Controls:** The provider-free positive fixture recognizes a trace-free
`insufficient_budget` result as `pre_dispatch_rejected`, stops validly, and
does not increment provider dispatch count. Existing ambiguity and corrupt
checkpoint controls must still terminate invalid. A budget rejection carrying
a provider trace is not accepted as pre-dispatch evidence.

**Readout:** pass only when the durable checkpoint has terminal state `stopped`,
terminal reason `scarcity_binding_pre_dispatch`, a final
`pre_dispatch_rejected` attempt with no trace, and provider dispatch count below
16. Preserve every prior committed action, settlement, budget trajectory,
timing, usage, and shared-client trace. The dashboard must show the terminal
state and concrete history.

**External-call budget:** maximum 16 calls, serial width 1, no retry or
fallback. Plan 10 observed 7.2–8.6 seconds and subscription-included provider
cost USD 0 per call; those are observations rather than guaranteed bounds.
Checkpoint after every settlement; resume identity is the frozen run ID plus
acknowledgement. Stop immediately on the scarcity boundary or any ambiguity.

**Non-claims:** This single cell does not establish reliability, a scarcity
effect on behavior, a comparison baseline, or a production parameter.

### Authentic result (2026-08-12)

The frozen midpoint probe passed from clean pushed AE3 revision `49ce2a4` and
the exact accepted shared-client revision. Seven Luna calls settled and
committed. The eighth attempt stopped at a trace-free pre-dispatch
`insufficient_budget` result, leaving `0.002196` budget. Custody records seven
provider dispatches, not eight, with no retry, fallback, MCP, ambiguity, or
invalid state.

The dashboard showed `7/16`, custody `stopped`, the concrete action history,
and remaining budget with no console errors or failed requests. The durable
compact result is `authentic_midpoint_probe.json`; content hashes there bind
the locally retained full receipt and checkpoint.

This makes the midpoint eligible for a later calibration/control design. It
does not yet establish that scarcity changes behavior or select a production
parameter.

## Files Affected

- `src/agent_ecology3/analysis/scarcity_calibration.py` (create)
- `src/agent_ecology3/simulation/recovery.py` (modify)
- `scripts/run_recoverable_evaluation.py` (modify)
- `tests/test_scarcity_calibration.py` (create)
- `tests/test_recoverable_poc.py` (modify)
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
