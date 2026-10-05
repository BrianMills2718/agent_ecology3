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

Brian (2026-10-05): cooperation should pay only at scale and over long
horizons, and subscription capacity and bugs get worked out on smaller runs
first ("just start the runs now if we are ready"). This plan runs
progressively larger and longer ecologies to find what breaks. It is an
observation and bug-finding plan: no stop rule or thesis verdict.

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
