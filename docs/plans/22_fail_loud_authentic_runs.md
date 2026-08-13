# Plan #22: Fail-Loud Authentic Runs

**Status:** Implementation Complete — browser observation and Luna canary pending
**Type:** prototype repair
**Priority:** Critical
**Blocked By:** None
**Blocks:** Another operator-observed run

## Gap

**Current:** The dashboard-launched Plan 21 worker survived long enough to be
resumed after its source worktree was removed. Its deleted current directory
caused all 14 shared-client calls to fail locally before Codex dispatch, but the
runtime substituted `query_kernel` actions, committed them, and displayed them
as successful agent decisions.

**Target:** Authentic runs use a durable worker directory and stop invalid on
the first LLM, schema, decision-gate, or selected-action failure. The existing
dashboard labels historical substitutes as untrusted rather than successful.

**Why:** Another paid run is not decision-ready until a failure cannot masquerade
as ecology behavior.

## References Reviewed

- `CLAUDE.md` - canonical repo instruction and authentic-run contract
- `scripts/run_recoverable_evaluation.py` - paused worker lifecycle and receipt owner
- `src/agent_ecology3/world/world.py` - LLM settlement and loop substitution paths
- `src/agent_ecology3/simulation/recovery.py` - attempt custody and terminal state
- `src/agent_ecology3/dashboard/server.py` - existing operator projection
- `docs/MVP_ROADMAP.md` - initiative outcome and selected frontier
- `docs/LINEAGE_AND_RESTARTS.md` - failure-history authority

## Files Affected

- `CLAUDE.md`
- `scripts/run_recoverable_evaluation.py`
- `src/agent_ecology3/world/world.py`
- `src/agent_ecology3/simulation/recovery.py`
- `src/agent_ecology3/dashboard/server.py`
- focused tests in `tests/`
- this plan, the plan index, roadmap, Plan 21 evidence, and restart lessons

## Implementation Order

1. Launch workers from their durable run directory with an explicit
   `LLM_CLIENT_PROJECT`, never a removable worktree cwd.
2. Classify known local `FileNotFoundError` failures as pre-dispatch, refund the
   reservation, and preserve the original error.
3. Make `fail_closed_no_substitute` terminal for returned LLM failures, missing
   structured decisions, decision-gate rejection, and ambiguous dispatch.
4. Render fallback-origin activity as untrusted/failed in the existing
   dashboard while preserving archive, controls, artifacts, and evidence.
5. Run provider-free focused checks, then observe the repaired failure state in
   the browser. A new Luna canary remains a separate spend authorization.

## Acceptance Criteria

- [x] Worker cwd and shared-client project identity remain valid after its
  launching worktree is removed.
- [x] A pre-dispatch local failure makes zero confirmed dispatches, refunds its
  reservation, stops after one attempt, and records invalid custody.
- [x] A settled rejection or invalid/missing decision cannot invoke or commit a
  substitute action under `fail_closed_no_substitute`.
- [x] Historical fallback rows are visibly untrusted and not counted as
  successful agent decisions.
- [ ] Focused provider-free tests and one rendered failure-state observation pass.
- [x] No provider call is made during implementation or verification.

## Non-goals

- Removing legacy fallback behavior from explicitly provider-free fixtures or
  historical parsers.
- Replacing AE3 principals with Codex agents, refactoring the executable-loop
  architecture, adding a dashboard, or production hardening.
- Running another 14-call ecology before a separately authorized one-call
  canary proves the repaired authentic boundary.

## Preserved Incident Evidence

`/home/brian/.local/state/agent_ecology3/plan21_luna_dashboard_20260813_183636/`
is immutable evidence of this failure. Its receipt claims completion, but it has
14 `llm_syscall_error` events, zero shared-client receipts, 14 fallback-origin
`query_kernel` actions, and no agent-created artifacts or value movement.

## Implementation Evidence

- All repository tests pass provider-free; the four changed source modules pass
  focused `mypy` and `git diff --check` is clean.
- A served read-only projection of the preserved incident reports 14/14
  substitutes, `success=false` for evidence, and
  `local_action_success=true` for the retained mechanical outcome.
- The served HTML contains the invalid-evidence banner and
  `substitute — not model-selected` activity label while archive selection,
  artifacts, Evidence, and launch remain present.
- No browser engine is installed in this execution environment, so visual
  browser observation remains explicitly outstanding.
- Repository-wide `mypy` remains red on 26 pre-existing errors in seven
  unrelated files; the changed modules are clean.
