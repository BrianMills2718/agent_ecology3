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

## Toward the target (not yet built)

Resident Codex or Claude Code agents acting through the MCP bridge, and a task
source whose later tasks build on earlier work. Research on both is in
progress; their findings set the next runs here.

## Run log

| Run | Result | Evidence |
|---|---|---|
