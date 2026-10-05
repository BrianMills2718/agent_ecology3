---
plan_id: "agent-ecology3#25"
dependencies: ["agent-ecology3#24"]
dependencies_reviewed: "2026-10-05"
---
# Plan #25: Scale Shakeout Toward a Long-Running Ecology

**Status:** 🚧 In Progress — first shakeout run
**Type:** exploratory PoC iteration
**Priority:** Critical
**Blocked By:** None
**Blocks:** Roadmap capability 4b (long-running ecology at scale)

## Why

Brian (2026-10-05): the current goal is to get the system working and the
agents behaving intelligently so it can scale; whether cooperation pays is a
later question that needs scale and long horizons. Subscription capacity and
bugs get worked out on smaller runs first ("just start the runs now if we are
ready"). Runs here are for finding bugs and judging agent behavior: no stop
rule or thesis verdict.

## Progress

| Step | State | Evidence |
|---|---|---|
| Scale shakeout run 1 (4 agents, 120 decisions) | done — clean; one visibility bug fixed | `run_bundles/plan25_shakeout_run1.tar.gz`; PR #73 |
| Live interaction graph (stopgap viewer) | done | Interactions tab, PR #75 |
| llm_client pin with session resume | done | `ea550d2`, PR #76 |
| `ae3_action` MCP server executes against the kernel and returns the result | next | see "Toward the target" |
| World Substrate living-view adapter | chosen (Brian: viewer only) | contracts and conditions below |
| Compounding task source (CodeFlowBench) | researched | see "Toward the target" |

## World Substrate living view (viewer only)

Agreed with the World Substrate session on 2026-10-05:

- Target `world-substrate-live-projection/v0` (initial snapshot plus ordered
  events with stable ids and leaf `changes`; applying the changes in order must
  reproduce the final state and hash) and a `world-substrate-living-scene/v1`
  profile, using the generic primitives in
  `docs/contracts/composed-living-scene-v1.md` (in world-substrate). Validate
  with `load_scene_contract()` and the frame builder against
  `tests/fixtures/living_scene/`. Do not target the legacy
  `evidence/renders/waltzman-demo-v0.html`.
- Pin world-substrate `33bd121`; do not edit world-substrate.
- Label the view "rendered with the World Substrate living view; outcomes from
  agent_ecology3": these are agent_ecology3 transitions, not World Substrate
  Engine commits.
- World Substrate froze renderer growth (its Decision 006). A missing market or
  payment primitive is a gap to raise with Brian. Incremental live updates in
  the generic renderer are unverified; start with periodically rebuilt
  retained bundles.

## Run 1: 4-agent shakeout (now)

- 4 Minimal-mode Luna-low principals, 120 decisions total (30 each), seed 25001,
  trading open, Plan 24's outside checker and task-bounty mint.
- New 40-task HumanEval bank `config/tasks/humaneval_scale_v1.jsonl` (seed
  25001, excludes Plan 24's 8 tasks), 10 statements owned by each agent.
- Prompt listing raised from 24 to 80 artifacts
  (`llm.loop_snapshot_artifact_limit`), because at 24 most task statements
  were invisible to agents.
- Launch: `scripts/run_recoverable_evaluation.py start --acknowledgement
  plan25/luna-low/scale-shakeout/v1 --target-attempts 120 --principal-count 4
  --cognition-mode minimal --policy-seed 25001 --starting-llm-budget 1.0`.

Known non-goal for this run: HumanEval tasks are independent, so this run
cannot show compounding. It finds scale bugs (prompt size, listing, timing,
serialization, cost per call) before the real target.

## Toward the target (researched 2026-10-05, not yet built)

**Resident agents (harness).** Recommended: Claude Agent SDK agents run through
`llm_client`, one resumed session per agent. Each tick the kernel sends an
agent its observations since its last turn; the agent acts only through the
`ae3_action` MCP tool (built-in tools disabled), and its session id is kept in
the kernel. Gaps found:

- AE3 pins `llm_client` 2867157, which cannot resume sessions. `llm_client`
  main already supports Claude `resume`/`session_id` and Codex
  `codex_session_mode=resume`, so the pin moves to main.
- `src/agent_ecology3/mcp/loop_action_server.py` only echoes the action back.
  It must execute against the kernel (identity fixed at launch, atomic
  settlement, receipt per tool call) and return the real outcome, so the
  agent sees what its action did.
- First check: 4 agents × 5 ticks; same session id every tick, every world
  change matches an `ae3_action` call, no built-in tool calls, and the agent
  refers to an earlier tick's result.
- Open risk: Anthropic's Agent SDK docs say products built on it should use API
  keys rather than claude.ai login; whether Brian's own research runs on his
  subscription are fine is unverified. Codex with ChatGPT login is the
  alternative route (MCP must be written into each agent's own Codex home).

**Work that compounds (task source).** No openly licensed benchmark has
dependencies between tasks through a shared library; the usable structure is
helper functions that build on each other inside a problem. Recommended:
CodeFlowBench-Comp (MIT; 986 Codeforces-derived problems, 2,103 helper
functions, 948 with declared `dependencies`, standard-library tests). Each
helper becomes a bountied task; a solution may declare which artifacts it
uses, the checker runs them together, and each used artifact's author earns a
royalty when a submission that uses it passes, so reuse pays instead of
bounty-stealing. Runner-up: ClassEval (MIT, 100 classes). Risks: weak tests
(median 2 per helper; strengthen from reference solutions), contamination, and
unverified Codeforces redistribution terms.

## Run log

| Run | Result | Evidence |
|---|---|---|
| `plan25_shakeout_run1` (seed 25001) | **System: clean.** 120/120 decisions committed, all model-selected (`llm_valid`), 0 local failures, 30 decisions per agent, prompt 21-26k tokens, median call 11.6 s, estimated internal charge USD 2.30 (actual USD 0, subscription). **Behavior: mechanical.** Actions were only read (42), write (39), submit (39); 28 of 40 tasks solved (8/7/6/7 per agent), 4 failed hidden tests, 9 paid cross-agent reads, no queries or transfers. **Bug found:** 7 passing submissions earned nothing because the task was already claimed and agents could not see claims; fixed by marking `bounty_claimed_by` on the task statement and in the artifact listing. | `run_bundles/plan25_shakeout_run1.tar.gz` |
