# Agent Ecology 3 Product Roadmap

```yaml
doc_role: active_authority
authority: canonical
status: active
delivery_maturity: local_prototype
current_stage: repeatable_local_workbench
created: 2026-08-13
updated: 2026-08-13
```

This is the current-direction front door for Agent Ecology 3. It preserves the
completed MVP as the canonical exemplar and selects the shortest path toward a
repeatable local agent-ecology workbench. Completed plans and evaluations are
evidence; they do not define the next priority.

## Outcome and operating bias

For Brian as the operator, change a one-off, CLI-oriented agent simulation into
a repeatable local workbench where he can launch bounded ecologies, understand
who did what and why value moved, reopen completed runs, compare useful runs,
and progressively explore richer scenarios without editing source code.

Rapid user-visible progress is the default. Reversible local choices advance
without recurring approval. Pause only for new model spend, external
publication or deployment, destructive scope, sensitive data, or a product
direction change that materially alters this outcome.

The current investment boundary is **local prototype**. Authentication,
multi-user hosting, production reliability, generalized security hardening,
database migration, broad viewport matrices, and scale engineering are not on
the critical path unless a real deployment or reproduced failure activates
them.

## Current truth

| Dimension | Current truth |
|---|---|
| Technical execution | Plan 22 passed a one-call Luna canary and a fresh 14-call Luna Medium run through the repaired fail-loud worker |
| Stakeholder reviewability | Brian reviewed the completed authentic run in the existing Ecosystem dashboard and said it looked fine |
| Stakeholder outcome | **Local MVP complete**: two agents acted live, value crossed principals, reusable artifacts were created and consumed, and the run completed in the same interface |
| Independent evidence | Plan 19 is independently signed off for this bounded local-MVP claim |
| Operational state | The dashboard launches paused, resumes explicitly, reaches truthful 14/14 custody, and reopens the new durable run after worker shutdown; the invalid Plan 21 incident remains preserved negative evidence |
| Claim boundary | Repeatable local workbench demonstrated by the Plan 19 and Plan 22 runs; no causal, comparative, population, or generalization claim |

## Canonical outcome exemplar

**Classification:** `canonical_outcome_exemplar`

- Starting state: merged AE3 `941c5cd`, reviewed `llm_client` `2867157`, two
  Minimal-mode principals, two discoverable priced opportunities, paused at
  0/14 calls.
- Operator action: Brian resumed the run from the existing dashboard.
- System transition: Luna selected 14 structured actions through the real
  runner and action executor.
- Inspectable result: the Ecosystem dashboard showed 14/14 successful
  decisions, three genuine `alpha_2 -> alpha_1` purchases totaling 5 scrip,
  seven agent-created artifacts, reuse of `alpha_1_analysis`, one mint
  submission, final balances 104/95, and completed custody.
- Durable evidence:
  `/home/brian/.local/state/agent_ecology3/plan19_luna_live_economic_mvp_v1/`
  plus [the Plan 19 sign-off](evaluations/19_live_economic_mvp_signoff.md).
- Evidence step-down: provider-free fixtures establish plumbing only; the
  authentic run establishes this one local observation only.
- Known negative case: an agent reading its own priced artifact is displayed
  as a purchase even though no cross-principal transfer occurs. This is a
  bounded presentation defect, not a failed economic interaction.

## Capability sequence and success criteria

| Order | Capability outcome | Class/state | Success criterion | Promotion trigger |
|---|---|---|---|---|
| 0 | Authentic live economic MVP | vertical / **complete** | Brian can launch, watch, understand, and inspect one completed two-agent run without raw JSON | Satisfied by Plan 19 |
| 1 | Reopen any preserved run | direct blocker / **complete** | After shutting down the original worker, a fresh process lists and opens the single Plan 19 receipt read-only with the same 14 actions, balances, artifacts, lifecycle, and evidence; zero model calls | Satisfied by Plan 20 |
| 2 | Launch another bounded run from the existing dashboard | vertical / **complete** | Brian starts a fixed-profile run paused, sees model/call ceiling/exposure, and reaches the live Ecosystem view without using a CLI; no dispatch occurs before explicit Resume | Satisfied by Plan 21 |
| 3 | Fail-loud repeat-run boundary | direct blocker / **complete** | A durable worker stops invalid on the first authentic-boundary failure and never presents a substitute as model behavior | Satisfied by Plan 22 canary and fresh 14-call run |
| 4 | Explain relationships when the activity feed stops being enough | conditional | A compact economic summary answers who paid whom, for what, how balances changed, and which artifacts were reused; add a synchronized graph only if Brian cannot follow a richer run from the list | A real run contains relationships that Brian finds hard to understand |
| 5 | Explore scenarios without source edits | vertical / conditional | Two versioned scenario configurations change opportunities or rules while reusing the same runner, dashboard, and receipt contract | Brian selects scenario exploration as more valuable than repeating the canonical profile |
| 6 | Compare or replicate runs | exploration required | A preregistered question, representative cells, equal call exposure, valid receipts, and an independently signed-off comparison support only the stated decision | Brian needs evidence beyond one-run product observation and approves the spend |
| 7 | Expand ecology size and dynamics | conditional | A 4–8 agent run remains legible, bounded, and economically active; scaling work addresses only reproduced limits | Two-agent runs are repeatable and the next uncertainty is network behavior |
| 8 | Internal pilot or external release | deliberately deferred | Deployment target, users, data, access, uptime, and release authority are explicit before production controls enter scope | A real remote or multi-user consumer exists |

Success criteria derive from the explicit user outcome and the observed current
boundary. Release-only controls activate only at capability 7; evaluation
controls activate only at capability 5.

## Binding implementation order

1. Generalize the existing receipt-backed review seam from a hard-coded matched
   pair to a run library that can open the canonical single Plan 19 run.
2. Prove that path from a fresh process after shutting down the live worker.
3. Extend the same dashboard with one fixed-profile, paused-by-default launch
   action; do not build a configuration panel zoo.
4. Repair the reproduced deleted-cwd and substitute-success defects with a
   provider-free fail-loud vertical.
5. After separate authorization, prove the boundary with one Luna call before
   exposing another 14-call run. **Complete.**
6. Observe one newly launched valid run through the same screen. **Technically
   complete; Brian's usefulness judgment remains.**
7. Select scenario exploration, comparison, or larger ecologies based on the
   next concrete operator question—not because infrastructure exists.

No work-unit graph or parallel program is justified for the current
single-contributor sequence. Future implementation goals receive a bounded
design. The technical repeat-run frontier is complete; the current frontier is
Brian's review of the preserved Plan 22 run before selecting any conditional
capability.

## Selected execution frontier

**Goal:** Have Brian judge whether the repaired, repeatable dashboard run is
understandable and useful enough to accept the local MVP.

Backward path:

```text
Brian accepts the repeatable local MVP
  <- Brian reviews the reopened Plan 22 run in the existing dashboard
  <- a fresh 14-call run completes with authentic actions and zero substitutes
  <- one Luna canary proves durable cwd and fail-loud custody
  <- provider-free checks prove the first failure stops after one attempt
```

The implementation boundary is complete; the remaining frontier is stakeholder
acceptance. Existing capabilities apply as follows:

| Capability | Canonical seam | Disposition | Adoption proof |
|---|---|---|---|
| Operator UI | existing Ecosystem dashboard | accepted implementation | Completed run shows 14 readable decisions and preserves raw Evidence |
| Worker lifecycle | recoverable paused worker | accepted implementation | Durable run reopens after the original worker exits |
| Spend boundary | hard call cap, fixed Luna profile, explicit Resume | preserved | Canary passed before exactly 14 repeat-run dispatches |

**Next decision handoff:** Brian reviews
`plan22_luna_mvp_20260813_193248` and decides whether the activity is
understandable and useful. If accepted, choose the next conditional capability
from a concrete operator question. If rejected, repair only the specific
comprehension or behavior defect observed. No scenario work, graph, deployment,
or production hardening is required first.

## YAGNI guardrails

Do not add the following until their trigger above is real:

- WebSockets or a new frontend framework;
- a second dashboard;
- database-backed run storage;
- authentication, tenancy, cloud deployment, or production observability;
- generic workflow/orchestration abstractions;
- interaction graphs before list comprehension fails;
- broad evaluation matrices or more model calls without a decision they can
  change;
- generalized security, compliance, performance, or scale hardening.

Baseline invariants remain: no secret exposure, no accidental publication,
exact destructive targets, visible failures, and recoverable Git checkpoints.

## Course and failure rules

| Observation | Disposition |
|---|---|
| A fresh process cannot reopen Plan 19 | Repair receipt discovery/projection before adding launch controls |
| Dashboard and receipt disagree | Treat the dashboard as untrusted and repair adoption before another run |
| Launch requires many configuration choices | Freeze one useful profile; defer general scenario authoring |
| Another authentic run produces no useful interaction | Revisit opportunity discoverability before visualization or scale |
| Richer activity is hard to explain | Promote the compact economic summary; graph only if still needed |
| Work spends two increments on tests/docs/infrastructure without a new visible operator capability | Return immediately to the selected browser journey |
| A remote or multi-user consumer appears | Replan maturity and activate only the necessary pilot controls |

## Authority and history

- This file owns initiative outcome, phase order, success criteria, and selected
  frontier.
- [Plan 19](plans/19_live_economic_mvp.md) and its
  [independent sign-off](evaluations/19_live_economic_mvp_signoff.md) own the
  completed MVP implementation and evidence.
- [Plan index](plans/CLAUDE.md) is navigation and historical status.
- [Lineage and restarts](LINEAGE_AND_RESTARTS.md) remains authoritative for
  AE1/AE2/AE3 lineage and restart failure history.
- [Plan 20](plans/20_single_run_archive_reopen.md) owns the completed archive
  implementation and focused browser evidence.
- [Plan 21](plans/21_dashboard_launch.md) owns the completed paused dashboard
  launch and zero-dispatch browser evidence.
- [Plan 22](plans/22_fail_loud_authentic_runs.md) owns the fail-loud repair,
  authentic canary, repeat-run receipt, and durable reopen evidence.
