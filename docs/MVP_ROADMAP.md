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
| Technical execution | Luna Medium, structured actions, recovery, hard call caps, live projection, graceful shutdown, and receipt custody pass |
| Stakeholder reviewability | Brian reviewed the completed authentic run in the existing Ecosystem dashboard and said it looked fine |
| Stakeholder outcome | **Local MVP complete**: two agents acted live, value crossed principals, reusable artifacts were created and consumed, and the run completed in the same interface |
| Independent evidence | Plan 19 is independently signed off for this bounded local-MVP claim |
| Operational state | The dashboard can reopen preserved runs and launch the frozen profile paused; `plan21_luna_dashboard_20260813_183636` is prepared at 0/14 with zero provider dispatches pending separate Resume authorization |
| Claim boundary | One successful local run; no causal, comparative, population, or generalization claim |

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
| 3 | Explain relationships when the activity feed stops being enough | conditional | A compact economic summary answers who paid whom, for what, how balances changed, and which artifacts were reused; add a synchronized graph only if Brian cannot follow a richer run from the list | A real run contains relationships that Brian finds hard to understand |
| 4 | Explore scenarios without source edits | vertical / conditional | Two versioned scenario configurations change opportunities or rules while reusing the same runner, dashboard, and receipt contract | Brian selects scenario exploration as more valuable than repeating the canonical profile |
| 5 | Compare or replicate runs | exploration required | A preregistered question, representative cells, equal call exposure, valid receipts, and an independently signed-off comparison support only the stated decision | Brian needs evidence beyond one-run product observation and approves the spend |
| 6 | Expand ecology size and dynamics | conditional | A 4–8 agent run remains legible, bounded, and economically active; scaling work addresses only reproduced limits | Two-agent runs are repeatable and the next uncertainty is network behavior |
| 7 | Internal pilot or external release | deliberately deferred | Deployment target, users, data, access, uptime, and release authority are explicit before production controls enter scope | A real remote or multi-user consumer exists |

Success criteria derive from the explicit user outcome and the observed current
boundary. Release-only controls activate only at capability 7; evaluation
controls activate only at capability 5.

## Binding implementation order

1. Generalize the existing receipt-backed review seam from a hard-coded matched
   pair to a run library that can open the canonical single Plan 19 run.
2. Prove that path from a fresh process after shutting down the live worker.
3. Extend the same dashboard with one fixed-profile, paused-by-default launch
   action; do not build a configuration panel zoo.
4. Observe one newly launched run through the same screen. Provider-free checks
   prove launch plumbing; an authentic run requires a new exact spend approval.
5. Repair only defects reproduced in that journey.
6. Select scenario exploration, comparison, or larger ecologies based on the
   next concrete operator question—not because infrastructure exists.

No work-unit graph or parallel program is justified for the current
single-contributor sequence. Future implementation goals receive a bounded
design; the current frontier is only the explicit Resume authorization and
authentic observation of an already prepared run.

## Selected execution frontier

**Goal:** Observe the prepared dashboard-launched run after separate Luna authorization.

Backward path:

```text
Brian judges whether the workbench repeats the useful ecology
  <- prepared run is observed from 0/14 through terminal custody
  <- Brian explicitly presses or authorizes Resume
  <- fixed Luna Medium profile retains its 14-call hard ceiling
  <- plan21_luna_dashboard_20260813_183636 remains paused with zero dispatches
```

The product boundary is complete; the remaining frontier is a human spend
decision followed by authentic observation. Existing capabilities apply as
follows:

| Capability | Canonical seam | Disposition | Adoption proof |
|---|---|---|---|
| Operator UI | live Ecosystem at port 9021 | reuse | Brian observes the prepared run and terminal replay |
| Worker lifecycle | recoverable paused worker | reuse | Run begins at the preserved 0/14 checkpoint |
| Spend boundary | hard call cap, fixed Luna profile, explicit Resume | preserve | No dispatch until separate authorization; never exceed 14 |

**Next decision handoff:** Brian may authorize Resume for exactly the prepared
Luna Medium run above under the existing 14-call ceiling and Plan 19 profile.
Until then, keep it paused. No new design, scenario work, graph, deployment, or
hardening is required before that observation.

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
