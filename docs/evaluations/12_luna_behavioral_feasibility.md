# Evaluation 12: Luna Behavioral Feasibility Probe

**Stage:** Preregistered exploratory feasibility probe
**Execution:** Not authorized and not run
**Decision owner:** Brian Mills

## Claim and decision

The falsifiable claim is that, in a two-principal AE3 world with the accepted
Plan 11 scarcity budget, prescribed and minimal cognition can each complete an
interpretable 16-attempt trajectory with real economic opportunities and
truthful scarcity/action custody.

The decision is instrument feasibility only:

- **continue:** both cells are valid, scarcity is observed or approached
  truthfully, and the paired trajectories expose concrete behavior that could
  support a later replicated comparison;
- **revise:** both cells are valid but the horizon contains no meaningful
  economic opportunity or interpretable behavioral distinction; or
- **invalid:** either cell has route, custody, recovery, source, or engagement
  failure.

This probe cannot establish a cognition effect, causality, reliability,
generalization, statistical significance, or a production parameter.

## System and matched pair

One matched pair uses seed `24120`. Prescribed runs first, then minimal. Each
cell has two principals, `0.033192` starting LLM budget per principal, and stops
after exactly 16 settled attempts or any terminal invalid boundary. This gives
each principal approximately the eight-attempt opportunity calibrated in Plan
11 while preserving bilateral interaction.

Everything except the cognition package remains fixed: exact Luna Medium,
medium reasoning, CLI, structured action schema, initial world, seed, runner,
shared-client revision, no MCP, zero retries, and no fallback. Condition order
is fixed and temporal drift is a known limitation of the single pair.

## Readout

Primary feasibility checks per cell:

- exactly 16 committed, uniquely traced provider attempts;
- 6–10 attempts per principal, so one principal cannot consume the assay;
- no provider, schema, custody, replay, cache, retry, fallback, or auxiliary
  scorer failure;
- at least one successful non-query economic action across the pair; and
- inspectable state, action, budget, and artifact trajectories in the existing
  dashboard and retained receipts.

Scarcity binding, action composition, artifact production/consumption,
transfers, balances, and downstream value are descriptive. No difference
threshold is preregistered because one pair cannot estimate an effect.

## Controls and invalidation

Before dispatch, the provider-free design validator must pass and mutation
controls must reject excess calls, retries, the old uncalibrated budget, loss
of bilateral interaction, and any causal decision label. Plan 10 recovery and
Plan 11 pre-dispatch scarcity controls remain passing.

Any missing/duplicate trace, source mismatch, ambiguous dispatch, corrupt
checkpoint, replacement call, wrong condition, wrong seed, or wrong budget
invalidates the probe. Preserve partial evidence and do not rerun a cell under
Evaluation 12.

## Call and evidence contract

Maximum exposure is one pair × two conditions × 16 attempts = **32 serial Luna
calls**. Retry, repair, fallback, and MCP are prohibited. Subscription-included
provider cost and internal budget charges are recorded per attempt; no USD cost
claim is assumed in advance. Each cell begins paused from a clean pushed source
revision and uses a unique exact acknowledgement.

Full runtime evidence remains checkpointed outside source discovery; compact
receipts, frozen inputs, reproduction output, and SHA-256 identities are stored
under `docs/evaluations/evidence/12_luna_behavioral_feasibility/`.

No execution is authorized by this document. A human must explicitly approve
the exact 32-call ceiling after the implementation revision and zero-provider
preflight are reviewed. Any decision from completed evidence additionally
requires fresh `eval-decision-signoff`.
