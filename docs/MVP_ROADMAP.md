# Agent Ecology 3 Product Roadmap

```yaml
doc_role: active_authority
authority: canonical
status: active
delivery_maturity: local_prototype
current_stage: outside_scored_comparison
created: 2026-08-13
updated: 2026-10-05
```

This is the current-direction front door for Agent Ecology 3. It preserves the
completed MVP as the canonical exemplar and selects the shortest path toward a
repeatable local agent-ecology workbench. Completed plans and evaluations are
evidence; they do not define the next priority.

**2026-10-05 redirect:** the frontier no longer waits on a judgment of whether a
run is *interesting*. Runs are now judged by an outside automatic score and a
solo baseline: did the same agents earn more by trading than by working alone?
[Plan 24](plans/24_external_score_vs_solo.md) is the living plan for that
redirect and owns its milestones, stop rule, and active slice.

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
| Technical execution | Long-lived Codex agents keep one session each, act only through the kernel's `ae3_action` tool, and test their own code in a private folder; 8 agents × 20 turns run cleanly (`plan25_resident_codex_run2`, `plan25_codeflow_run1`) |
| Stakeholder reviewability | Every run reopens read-only in the dashboard; its Living view (World Substrate renderer) shows agents moving between places, their turn notes, and royalties as messages between agents |
| Stakeholder outcome | **Thesis not yet tested at its scale.** Plan 24's outside-scored checker, trading switch and comparison view work. Its tiny setting (2 agents, 28 decisions, 8 independent tasks) showed no trading gain (tie, tie, solo), but that setting leaves no room for division of labor or compounding, so it does not test the thesis, which concerns scale and long horizons (Brian, 2026-10-05) |
| Independent evidence | Plan 19 and Plan 23 are independently signed off for their bounded technical claims |
| Operational state | Latest run `plan25_codeflow_run1` completed 160/160 agent-turns; evidence bundles (redacted where needed) are in `evaluations/evidence/run_bundles/` |
| Claim boundary | Working system observations only: no causal, comparative, population, or emergence claim |

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
  (durable copy: [run bundle](evaluations/evidence/run_bundles/plan19_luna_live_economic_mvp_v1.tar.gz))
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
| 4 | Interesting emergent interaction | **closed 2026-10-05** | Superseded: "interesting" cannot test the thesis | Plan 23 retained as plumbing evidence; replaced by row 4a |
| 4a | Outside-scored trading-vs-solo comparison | vertical / **complete 2026-10-05 (instrument)** | The dashboard shows, for three matched pairs, tasks solved by an outside checker per call with trading on vs off | Built and used once at toy scale; reuse as an observation lens, not a verdict |
| 4b | Working, intelligent ecology at scale | vertical / **in progress (Plan 25)** | Resident agents that keep memory and test their own work run for a long horizon on work whose value compounds, without system bugs, and Brian can watch them in the World Substrate living view | Brian's direction 2026-10-05; Plan 25 steps 1-4 |
| 5 | Explain relationships when the activity feed stops being enough | conditional | A compact economic summary answers who paid whom, for what, how balances changed, and which artifacts were reused; add a synchronized graph only if Brian cannot follow a richer run from the list | Brian cannot follow Plan 23 or a richer run from the list |
| 6 | Explore scenarios without source edits | vertical / conditional | Two versioned scenario configurations change opportunities or rules while reusing the same runner, dashboard, and receipt contract | Brian selects scenario exploration as more valuable than repeating the canonical profile |
| 7 | Compare or replicate runs | exploration required | A preregistered question, representative cells, equal call exposure, valid receipts, and an independently signed-off comparison support only the stated decision | Brian needs evidence beyond one-run product observation and approves the spend |
| 8 | Expand ecology size and dynamics | conditional | A 4–8 agent run remains legible, bounded, and economically active; scaling work addresses only reproduced limits | Two-agent runs are repeatable and the next uncertainty is network behavior |
| 9 | Internal pilot or external release | deliberately deferred | Deployment target, users, data, access, uptime, and release authority are explicit before production controls enter scope | A real remote or multi-user consumer exists |

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
6. Observe one newly launched valid run through the same screen. **Complete.**
7. Repair the reproduced repetitive-strategy and missing-read-memory defects,
   then obtain one rubric-passing reciprocal-interaction candidate. **Complete.**
8. ~~Obtain independent sign-off and Brian's interesting-behavior judgment.~~
   Sign-off done; the judgment was replaced on 2026-10-05 by step 8a.
8a. Follow [Plan 24](plans/24_external_score_vs_solo.md): repair blockers,
   one-hour landscape check, outside-score oracle and solo switch, then three
   matched pairs under a pre-set stop rule.
9. Select scenario exploration, comparison, or larger ecologies based on the
   next concrete operator question—not because infrastructure exists.

No work-unit graph or parallel program is justified for the current
single-contributor sequence. Future implementation goals receive a bounded
design. The technical repeat-run and reciprocal-interaction probes are complete;
the current frontier is independent verification plus Brian's review of the
preserved Plan 23 candidate.

## Selected execution frontier

**Current goal (Brian, 2026-10-05):** get the system working and the agents
behaving intelligently, so it can scale. Whether cooperation pays is not the
question yet; it needs scale and long horizons ("a little village of 3 people
trying to build a fire" does not need markets), so no stop rule or verdict is
attached to runs for now. Runs are for finding bugs and judging agent behavior.

Status ([Plan 25](plans/25_scale_shakeout.md) holds the run log and evidence):

1. **Scale shakeout: done.** The 4-agent single-call run was clean; it found
   that agents could not see claimed tasks (fixed).
2. **Resident agents: working.** Each agent is a long-lived Codex (default,
   ChatGPT subscription) or Claude Agent SDK session that keeps its own memory
   and acts only through the `ae3_action` MCP tool, which the kernel executes
   and answers. 8 agents × 20 turns completed cleanly and solved 80/80 tasks.
   Agents now write and run their own tests in a private folder before
   submitting (Codex history of `plan25_codex_shell_probe2`: 6 shell
   commands, repaired a failing solution before submitting).
3. **Work that compounds: working.** A local CodeFlowBench bank of helper
   tasks with dependencies; the checker links already-solved helpers and pays
   their authors royalties. 8 agents × 20 turns: 33/52 solved, 9 royalties to 7
   authors, every agent tested its own code (7-21 shell commands each). Next:
   rerun with the clearer task statements and solved-helper listing.
4. **Watching it: done, one gap.** The dashboard's Living view renders runs in
   World Substrate's world-agnostic living view (viewer only, pinned
   `33bd121`, labelled "rendered with the World Substrate living view;
   outcomes from agent_ecology3"): shared places, agents moving between them,
   and each agent's turn note as a bubble; live pages jump to the latest
   moment. Agents at the same place stack on one point, which needs a World
   Substrate renderer primitive (its renderer is frozen, Decision 006).

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
| A small, short comparison shows no cooperation gain | Not evidence against the thesis (wrong niche); scale and lengthen before judging |
| Richer activity is hard to explain | Promote the compact economic summary; graph only if still needed |
| Work spends two increments on tests/docs/infrastructure without a new visible operator capability | Return immediately to the selected browser journey |
| A remote or multi-user consumer appears | Replan maturity and activate only the necessary pilot controls |

## Authority and history

- This file owns initiative outcome, phase order, success criteria, and selected
  frontier.
- [Plan 19](plans/19_live_economic_mvp.md) and its
  [independent sign-off](evaluations/19_live_economic_mvp_signoff.md) own the
  completed MVP implementation and evidence.
- [Plan index](plans/AGENTS.md) is navigation and historical status.
- [Lineage and restarts](LINEAGE_AND_RESTARTS.md) remains authoritative for
  AE1/AE2/AE3 lineage and restart failure history.
- [Plan 20](plans/20_single_run_archive_reopen.md) owns the completed archive
  implementation and focused browser evidence.
- [Plan 21](plans/21_dashboard_launch.md) owns the completed paused dashboard
  launch and zero-dispatch browser evidence.
- [Plan 22](plans/22_fail_loud_authentic_runs.md) owns the fail-loud repair,
  authentic canary, repeat-run receipt, and durable reopen evidence.
- [Plan 23](plans/23_emergent_interaction.md) owns the reciprocal-interaction
  rubric, read-memory repair, and candidate receipt; closed 2026-10-05 as
  plumbing evidence.
- [Plan 24](plans/24_external_score_vs_solo.md) owns the outside-scored
  comparison milestones, stop rule, and active slice.
