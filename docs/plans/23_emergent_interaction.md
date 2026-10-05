---
plan_id: "agent-ecology3#23"
dependencies: []
dependencies_reviewed: "2026-09-15"
---
# Plan #23: Emergent Economic Interaction

**Status:** ✅ Closed — plumbing evidence, not emergence (2026-10-05)
**Type:** exploratory PoC iteration
**Priority:** Critical
**Blocked By:** None
**Blocks:** None (superseded by [Plan 24](24_external_score_vs_solo.md))

## Claim and Decision

**Claim:** With accurate payoff guidance and complementary visible information,
two unassigned Minimal-mode Luna principals can produce at least one authentic
cross-agent adaptation chain within 14 decisions without prescribed roles,
forced exploration, retries, fallback actions, or substitute decisions.

**Decision:** Promote the first passing run to Brian's dashboard review. If at
most three fresh 14-call development runs fail, stop spending and redesign the
economic mechanism rather than adding prompt pressure or visualization.

**Unit:** One durable two-principal run. The negative baseline is
`plan22_luna_mvp_20260813_193248`; the corruption control is the invalid Plan 21
fallback run. This is an exploratory local-PoC claim, not evidence that the
behavior generalizes across seeds, models, populations, or longer horizons.

## Reproduced Failure

The valid Plan 22 repeat run committed 14 model-selected actions, but nine were
versioned strategy writes. It had action entropy `1.198`, one cross-principal
paid read worth 2 scrip, no direct transfer, no paid consumption of an artifact
created during the run, and zero mint downstream value. The exact prompts make
strategy revision salient while failing to explain that only another
principal's paid use creates artifact revenue. The two seeded opportunities are
generic advice rather than complementary economic information.

## Minimal Intervention

1. Explain existing payoff mechanics accurately: external paid reads transfer
   scrip; self-reads do not; writes have no payoff unless another principal
   chooses to use them; the mint auction will not resolve during this bounded
   run.
2. Keep principals unassigned and action choice open. Do not add roles,
   objectives, action sequences, forced exploration, or deterministic policy.
3. Replace generic starter advice with complementary market evidence and a
   validation method. These create an opportunity but select no action.
4. Freeze a new exact Plan 23 acknowledgement at Luna Medium, Minimal mode, two
   principals, 14 calls, seed `24230`, and `0.033192` budget per principal.
5. Launch paused, inspect `0/14`, resume, then inspect full traces, receipt,
   emergence metrics, and the rendered dashboard.

## Pre-Registered Readout

All hard criteria must pass:

| Construct | Threshold | Failure action |
|---|---|---|
| Authentic custody | 14 provider-settled and committed decisions; zero retries, fallback models, fallback/gate/recovery substitutions, or invalid actions | Invalidate and repair custody only |
| Endogenous market use | At least one cross-principal paid read of an artifact created during the run | Revise incentives or observability |
| Adaptation chain | After consuming another principal's run-created output, the buyer makes a materially different productive, trading, or mint action whose content or target uses the acquired information | Trace-review fail |
| Non-degeneracy | At least three decision action types and no one type above 60% of decisions | Revise salience or mechanism |
| Human interest | The activity can be summarized as a contingent multi-agent story, not independent repetitive actions | Do not promote |

The first four are the primary gate. Human interest is the final stakeholder
gate. Seeded-fixture purchases do not satisfy endogenous market use. Merely
writing a differently named artifact does not satisfy adaptation.

## Controls and Trace Contract

- Positive detector control: existing provider-free emergence fixtures contain
  cross-agent value and reuse events and must remain measurable.
- Negative control: the Plan 22 baseline must fail endogenous market use and
  the 60% dominance threshold.
- Corruption control: the Plan 21 fallback run must remain invalid evidence.
- Each authentic run must retain rendered prompts, structured raw responses,
  parsed actions, model and trace IDs, settlement status, local action results,
  event log, recovery checkpoint, shared-client receipts, cost, and latency.
- Post-run interpretation may explain failure but cannot relax these thresholds.
  Any intervention informed by a failed run is exploratory and needs a fresh
  run.

## Non-Goals

- Proving emergence generally or comparing models.
- Prescribing specialization, trade, reciprocity, or an action cycle.
- Turning on the mint scorer, whose current deterministic fallback is outside
  the authentic fail-loud contract.
- Adding dashboards, graphs, scenario editors, databases, deployment, or
  production hardening.

## Acceptance Evidence

### Development run 1 — valid but below threshold

`plan23_emergent_v1_run1` completed 14/14 on merged revision `fb8927c` with
14 shared-client receipts, zero retries, and zero fallbacks or substitutes. It
improved real interaction substantially over the Plan 22 baseline:

- `alpha_2` created priced `alpha_2_market_method`; `alpha_1` paid to read it
  twice, satisfying endogenous paid use of a run-created artifact;
- cross-paid consumption rose to 18 scrip across eight events and reuse-weighted
  artifact value rose to `30.476649`;
- the run produced four market/validation artifacts rather than nine versioned
  strategy artifacts.

It did not pass. Reads dominated 10/14 decisions (`71.4%`), only read and write
actions appeared, entropy fell to `0.863`, and both principals repeatedly paid
for the same artifact. Trace inspection showed that successful reads persisted
only action type and success; the next Luna turn received neither the target ID
nor the purchased content. The apparent later adaptation therefore cannot be
attributed to learned artifact content.

### Development intervention 2

Persist each action's selected target in existing private cognitive state. For
a successful authorized read, also retain a bounded 600-character observation
with artifact ID, type, owner, and content in the principal's state/notebook.
This reuses the current memory seam and does not add a memory service, action
policy, role, or forced exploration. Run 2 must satisfy the unchanged rubric.

### Development run 2 — promising behavior, invalid exposure

`plan23_emergent_v1_run2` made the purchased content available in each buyer's
next rendered Luna prompt and produced the intended reciprocal chain:

1. each principal bought the other's complementary seed evidence;
2. `alpha_1` created a priced validation framework from the validation method;
3. `alpha_2` created a priced opportunity forecast from the market signal;
4. both principals bought the other's run-created output;
5. after reading `alpha_2`'s forecast, `alpha_1` created its own falsifiable
   forecast, which `alpha_2` then bought.

At 11 committed decisions the partial metrics met the behavioral thresholds:
three action types, read dominance `54.5%`, entropy `1.435`, five cross-paid
events, and 11 scrip of cross-paid consumption. The run is nevertheless invalid
for promotion: richer memory increased prompt cost and `alpha_1` reached only
`0.000492` LLM budget, causing attempt 12 to stop pre-dispatch with
`scarcity_binding_pre_dispatch` before the fixed 14-call horizon.

### Development intervention 3

Use versioned acknowledgement `plan23/luna-medium/emergent-interaction/v2` with
`0.066384` LLM budget per principal. Keep the model, prompt, scenario, seed,
actions, memory, fail-loud policy, rubric, and 14-call ceiling unchanged. This
is exposure correction, not behavioral tuning.

### Development run 3 — all pre-registered technical criteria passed

`plan23_emergent_v2_run3` completed from merged revision `68dc440` with exact
14/14 provider-settled and committed Luna decisions, 14 shared-client receipts,
zero retries, zero fallback models, and zero fallback, gate-fallback,
recovery-fallback, substitute, or failed actions.

The run passed the unchanged behavioral gate:

- five cross-principal paid reads moved 12 scrip;
- three action types appeared: six reads, five event queries, and three writes;
- the largest action share was `42.9%`, below the `60%` ceiling, and loop action
  entropy was `1.531`;
- both principals bought complementary seed evidence, independently produced
  priced outputs, and bought each other's run-created outputs;
- after purchasing `alpha_2_opportunity_forecast`, `alpha_1` received its exact
  content in the next prompt, later wrote `alpha_1_opportunity_forecast`
  explicitly incorporating that evidence, and `alpha_2` bought it for 3 scrip;
- final balances were `alpha_1=104` and `alpha_2=96`.

Fresh Chromium at 1440x900 showed completed custody, all 14 activity rows, five
visible economic artifacts, working artifact-content inspection, and the raw
Evidence view after refresh with zero console errors or failed requests. After
the worker exited, a separate read-only process reopened the durable run with
the same 14 decisions and artifacts. The authoritative run directory is
`/home/brian/.local/state/agent_ecology3/plan23_emergent_v2_run3/` (durable copy:
[run bundle](../evaluations/evidence/run_bundles/plan23_emergent_v2_run3.tar.gz)).

This is a technically passing exploratory candidate, not a general emergence
claim. Independent sign-off is retained in
`../evaluations/23_emergent_interaction_signoff.md`; it passes the first four
pre-registered criteria and leaves the human-interest gate untouched. Brian's
judgment of whether the behavior is actually interesting remains pending.

## Closure (2026-10-05)

Brian delegated the human-interest gate ("i trust yoru recommendations what
ever they are"). Disposition: not accepted as an interesting-behavior exemplar.
The reciprocal chain follows from this plan's own payoff guidance and
complementary seeds (FAILURE_MODE_DOSSIER FM-01), and 5 of 14 decisions were
event-log queries. The run stays valid evidence that the market plumbing,
read memory, and custody work. [Plan 24](24_external_score_vs_solo.md) replaces
the interest judgment with an outside score and a solo baseline.
