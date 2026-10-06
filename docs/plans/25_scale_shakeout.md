---
plan_id: "agent-ecology3#25"
dependencies: ["agent-ecology3#24"]
dependencies_reviewed: "2026-10-05"
---
# Plan #25: Working, Intelligent Ecology at Scale

**Status:** 🚧 In Progress — M7 next (16 agents × 40 turns)
**Type:** durable living plan (company-planning `durable_solo`)
**Priority:** Critical
**Blocked By:** None
**Blocks:** Roadmap capability 4b

**Authority:** Brian, 2026-10-05: "i am not even trying to figure out whether
cooperation pays right now. just trying to get the system working and the
agents behaving intelligently so we can scale"; "we can figure out the
subscription capacity when we work out the bugs on smaller runs". This plan
owns Plan 25 milestones, the active slice and the run log;
[the roadmap](../MVP_ROADMAP.md) owns outcome and priority.
**Planning path:** `durable_solo` — one writer, work continues across sessions,
no parallel lanes, no shared contract changes.
**Selected controls:** continuity = this file; coordination = single lane;
reversibility = local, git-revertible; external effect = none (Codex runs on
Brian's ChatGPT subscription, nothing published beyond the public repo);
data = CodeFlowBench-derived text never committed (bank built locally,
bundles redacted).
**Artifact consumer / decision value:** the next session (what to run or
build next) and Brian (what the agents now do, visible in the Living view).
**Stage / investment boundary:** local prototype; no verdicts or benchmarks.
**Last outcome-bearing update:** 2026-10-05, `plan25_codeflow_run1` and PR #92.

## Outcome and boundaries

**Outcome:** For Brian, change "short runs of single-call agents that act
mechanically" into "long-lived agents that remember, test their own code and
build on each other's work, running cleanly at 8+ agents and watchable in the
Living view", within the local-prototype boundary.

**Canonical probe:** `uv run python scripts/run_resident_ecology.py --agents 8
--turns 20 --actions-per-turn 4 --task-bank <local CodeFlowBench bank>` →
every turn commits with one session per agent; each agent's Codex history shows
shell commands; royalties are paid when one agent's passing solution calls another's
helper; the dashboard's Living view replays it. Negative case: a turn error
stops the run as invalid with its reason (no substitutes).

**Success evidence:** run receipt (`lifecycle_state`, `shell_commands_from_history`
per agent), `royalty_paid` and `task_bounty_scored` events, Living view
screenshot, `make check` green on main.

**Non-goals:** any verdict on whether cooperation pays; benchmarks or
comparisons; Claude-based agent runs (they draw on Brian's Claude allowance);
renderer changes in World Substrate (its renderer is frozen); running the
economy on World Substrate's engine.

**Authority limits:** deleting run data or touching `~/.codex` needs Brian's
yes; nothing is published outside the repo.

## Architecture and capability invariants

- Agents act on the world only through the `ae3_action` MCP tool; the kernel
  authenticates each agent by a launch-time token, executes, records a
  `resident_action` receipt, and returns the real result.
- Resident Codex agents: one resumed session per agent; Codex home is
  run-owned with a private `sessions` directory (never linked to `~/.codex`);
  the writable folder `agents/<id>/work` is a sibling of the Codex home; homes
  are trimmed at run end keeping `thread_history_1.sqlite`.
- Failures stop the run (`ResidentRunError`); no substitute actions.
- The mint pays only on outside checker passes; dependency code is linked
  from already-solved helpers and their authors earn `mint.royalty_scrip`.
- Evidence bundles exclude `agents/` Codex homes and redact
  CodeFlowBench-derived text.

| Capability | Canonical seam | State | Evidence |
|---|---|---|---|
| Resident agents (Codex) | `src/agent_ecology3/simulation/resident.py`, `scripts/run_resident_ecology.py` | working | `plan25_resident_codex_run2`, `plan25_codeflow_run1` |
| Agents test own code | Codex `workspace-write` folder + instruction | working | `plan25_codex_shell_probe2`; 7-21 shell commands per agent in `plan25_codeflow_run1` |
| Compounding tasks + royalties | `scripts/build_codeflow_bank.py`, `world/mint.py` | built; real reuse not yet observed | `plan25_codeflow_run1`: 0 passing solutions called an earlier helper; its 9 royalties were a payout bug, fixed to require a call |
| Living view | `viz/world_substrate_view.py`, dashboard `/living-view` | working; stacking gap | PR #85, #91 |

## Milestones

| Milestone | Planning state | Output | Trigger / evidence |
|---|---|---|---|
| M1 Scale shakeout (single-call, 4 agents) | done | clean run; claimed-task visibility fix | `plan25_shakeout_run1`, PR #78 |
| M2 Resident agents (Claude, then Codex) | done | resumed sessions acting via the kernel | PRs #79, #81; runs below |
| M3 Isolation and cleanup | done | private Codex sessions; 5.2 GB reclaimed; agent sessions moved out of `~/.codex` | PR #88 |
| M4 Agents test their own code | done | writable folder + instruction; history-based count | PR #89 |
| M5 Compounding tasks and royalties | done | CodeFlowBench bank builder, linking, royalties | PRs #90, #91 |
| M6 Rerun on clearer tasks | done | 43/52 solved, 0 argument-count failures, 7 real helper calls; royalty payout and evidence bundling fixed | `plan25_codeflow_run2`, PRs #95 and this one |
| M7 Longer and larger runs | fully_specifiable_now (active) | 16 agents × 40 turns on a fresh 146-task bank | see Active slice |
| M8 Agents visible when they share a place | blocked_on_owner (approved by Brian 2026-10-05) | World Substrate spreads actors that move to the same place; then bump the pin here | [world-substrate#106](https://github.com/BrianMills2718/world-substrate/issues/106); its renderer files are under a live World Builder claim |
| M9 Economy on World Substrate's engine; cooperation verdicts | deliberately_deferred | — | Brian selects it |

## Active slice: M7 — 16 agents × 40 turns

**Visible result:** twice the agents, twice the turns, on a bank with more
cross-agent dependencies, replayed in the Living view.

**Steps:**
1. Bank (built locally): `uv run python scripts/build_codeflow_bank.py
   --agents 16 --problems 40 --seed 25201` →
   `~/.cache/agent_ecology3/codeflow_bank_a16_p40_s25201.jsonl` (146 tasks, 40
   problems, 94 cross-agent dependency links).
2. Run detached from the main checkout: `LLM_CLIENT_PROJECT=agent_ecology3 uv
   run python scripts/run_resident_ecology.py --agents 16 --turns 40
   --actions-per-turn 4 --task-bank <bank> --run-id plan25_codeflow_run3
   --port <free port> --keep-serving`.
3. `uv run python scripts/run_evidence.py report <run dir> --bank <bank>` and
   `... bundle ... --out docs/evaluations/evidence/run_bundles/plan25_codeflow_run3.tar.gz`;
   Living view screenshot at a genuine royalty frame; record in the run log.

**Focused check:** receipt `completed` with 640 agent-turns recorded, or a
named failure that is fixed and rerun once.

**Failure / containment:** a turn error stops the run invalid with its reason.

## Decisions and assumptions

| Choice | Disposition | Reason / evidence |
|---|---|---|
| Goal is a working, intelligent system at scale; no cooperation verdicts | human_set (Brian, 2026-10-05) | quotes above |
| Codex/Luna for resident agents, not Claude | agent_decided_reversible | the Sonnet run hit a Claude weekly limit (`plan25_resident_run1`) |
| Viewer-only use of World Substrate | human_set (Brian, 2026-10-05: "i agree on option 1") | `## World Substrate living view` below |
| CodeFlowBench text never committed | agent_decided_reversible | Codeforces redistribution terms unverified |
| Agents told to test before submitting | agent_decided_reversible | offered-only probe ran 0 commands; told, 6 (`plan25_codex_shell_probe1/2`) |
| Tests come from CodeFlowBench as published | assumption | its "solutions" are tokenized editorial text and cannot validate the tests; if many tests are wrong, failures will cluster on specific tasks |

## Human decisions

- **M8 (decided 2026-10-05):** Brian approved one small exception to World
  Substrate's renderer freeze so agents at the same place are spread in a
  ring. Filed as world-substrate#106 for the session that owns its renderer;
  when it merges, bump the pin in `viz/world_substrate_view.py` and re-check
  the Living view.

## World Substrate living view` below |
| CodeFlowBench text never committed | agent_decided_reversible | Codeforces redistribution terms unverified |
| Agents told to test before submitting | agent_decided_reversible | offered-only probe ran 0 commands; told, 6 (`plan25_codex_shell_probe1/2`) |
| Tests come from CodeFlowBench as published | assumption | its "solutions" are tokenized editorial text and cannot validate the tests; if many tests are wrong, failures will cluster on specific tasks |

## Human decisions

- **M8:** whether World Substrate's renderer gets one small exception to its
  freeze (an offset or gather ring on `actor.move_to`) so agents at the same
  place are all visible. Recommendation: yes. Default if unanswered: no change.

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

## Run log (evidence)

| Run | Result | Evidence |
|---|---|---|
| `plan25_codeflow_run2` (8 resident `codex/gpt-5.6-luna` agents, low effort, 20 turns, 4 actions per turn, v2 bank seed 25101: same 52 tasks, each stating its call shape and one example; agents see solved helpers) | **Completed 160/160 agent-turns**, one session per agent. Numbers from `scripts/run_evidence.py report` (run1 in brackets): **43 of 52 solved** [33]; 109 submissions [125], **64 failed** [89]: wrong answer 56 [60], **wrong argument count 0** [11], wrong argument type 1 [14], NameError 4, IndexError 2, AttributeError 1; 2 unpaid duplicates [3]. **Shell commands** from each agent's Codex history: alpha_1 19, alpha_2 6, alpha_3 16, alpha_4 15, alpha_5 21, alpha_6 25, alpha_7 14, alpha_8 15 (131) [128]. **Reuse:** where a needed helper was already solved by another agent, passing solutions called it **7 times** and rewrote it 3 [0 and 2]. **Royalties:** 11 paid (33 scrip) to alpha_3 3, alpha_4 2, alpha_5 2, alpha_6 2, alpha_2 1, alpha_7 1; 6 of them are genuine calls, 5 were paid by the old rule (run started before PR #95 required a call). Final scrip 132-172. Living view checked: no page errors, label present, 11 royalty frames; the tick badge covered the run name in the title (fixed in this PR); an agent standing at the market hides the "Market" label (World Substrate layout, same family as world-substrate#106). | `run_bundles/plan25_codeflow_run2.tar.gz` (built by `run_evidence.py bundle`, 0 bank leaks); `plan25_codeflow_run2_living_view.png` (genuine royalty: Agent 5's solution calls Agent 4's `go`) |
| `plan25_codeflow_run1` (8 resident `codex/gpt-5.6-luna` agents, low effort, 20 turns, 4 actions per turn, CodeFlowBench bank seed 25101: 52 helper tasks, 16 problems, 28 cross-agent dependency links) | **Completed 160/160 agent-turns**, one session per agent. **Agents tested their own code:** shell commands from each agent's Codex history: alpha_1 20, alpha_2 7, alpha_3 16, alpha_4 12, alpha_5 13, alpha_6 20, alpha_7 19, alpha_8 21 (128 total). **Work built on work: not yet.** Correction (2026-10-06, `scripts/run_evidence.py`): where a needed helper had already been solved by another agent, passing solutions called it 0 times and rewrote it 2 times; the 11/3 figures first written here were wrong. The 9 `royalty_paid` events (27 scrip, 7 authors) were paid to solutions that never called the helper: the payout checked only that the helper was not redefined. Fixed to require a call. **33 of 52 tasks solved**; 125 submissions, 89 failed hidden tests (mostly argument-count TypeErrors and assertions: CodeFlowBench helper statements never state how a helper is called), 3 unpaid duplicates. Final scrip 132-164. Fixes for the next run (same PR): each task states its arity and one example; the agent view lists solved helpers to call rather than redefine; the Living view shows each royalty as a message from the reusing agent to the author. Bundle rebuilt 2026-10-06 with `scripts/run_evidence.py`: the first version also carried about 120 hidden test cases inside checker failure reasons. | `run_bundles/plan25_codeflow_run1.tar.gz` (redacted: task and solution text withheld, agents/ excluded); `plan25_codeflow_run1_living_view.png` |
| `plan25_codex_shell_probe2` (1 Codex agent, 2 turns, 2 HumanEval tasks incl. /81) | **Agents now test their own code.** Resident Codex agents get a writable private folder (`sandbox_mode=workspace-write`) and an instruction to run each solution on the task's examples before submitting. The agent's Codex history (`thread_history_1.sqlite`) shows 6 shell commands: it wrote `test_grade.py`, failed 4 times on HumanEval/81, fixed it until the test passed, then tested /137; both passed the hidden tests. Probe 1 (same setup, testing only offered, not asked) recorded 0 commands: the agent skipped testing on easy tasks. Receipts now carry `shell_commands_from_history` per agent, and each agent's Codex home is trimmed at run end (thread history kept). | `run_bundles/plan25_codex_shell_probe2.tar.gz` (agent test files included, Codex home excluded) |
| Codex isolation fix (2026-10-05) | **Found by the session audit:** llm_client's `_create_codex_home` links each home's `sessions` to the user's real `~/.codex/sessions` (deliberately, so throwaway homes cannot lose transcripts). For persistent resident-agent homes this meant every agent indexed Brian's whole Codex history (2,572 threads, about 300 MB per agent, 5.2 GB over two runs) and 16 agent sessions were written among Brian's own sessions. Fixed in AE3: resident homes replace the link with a private `sessions` directory (test asserts it). Approved cleanup removed the bulk and the links, keeping each agent's own `thread_history_1.sqlite`; Brian's 2,580 session files were unchanged before and after. The 16 agent sessions remain in Brian's Codex history (not deleted). | this PR |
| `plan25_resident_codex_run2` (8 resident `codex/gpt-5.6-luna` agents, low effort, 20 turns, 4 actions per turn, 80-task bank) | **Completed 160/160 agent-turns**, one session per agent throughout; 279 actions (90 reads, 90 writes, 92 submits, 7 queries; 2 refused). **All 80 tasks solved**; 7 hidden-test failures repaired, 4 unpaid duplicates; 9 paid cross-agent reads, 0 transfers; final scrip 186-212. Turns took about 18-28 s late in the run. 8 Codex agents at this length run cleanly. | `run_bundles/plan25_resident_codex_run2.tar.gz` |
| `plan25_resident_codex_run1` (4 resident `codex/gpt-5.6-luna` agents, low effort, 10 turns, 4 actions per turn, 40-task bank) | **Completed 40/40 agent-turns** on the ChatGPT subscription; one session per agent throughout; 142 actions (45 reads, 50 writes, 47 submits; 2 refused over the turn limit). **39 of 40 tasks solved**; 7 submissions failed hidden tests and agents repaired and resubmitted (alpha_2 noted HumanEval/145's examples contradict its prose and derived the corrected sort key); 1 unpaid duplicate. 3 paid cross-agent reads, 0 transfers; final scrip 186-206. Turns took 33-48 s after a 192 s first turn. | `run_bundles/plan25_resident_codex_run1.tar.gz` |
| `plan25_resident_codex_probe3` (2 resident `codex/gpt-5.6-luna` agents, low effort, 2 turns, 2 actions per turn) | **Passed.** Each agent kept one Codex session across turns (resumed via llm_client `codex_session_mode=resume` with a persistent per-agent `codex_home` built by llm_client's `_create_codex_home`); every world change is a kernel receipt from an ae3_action call; memory carried over (alpha_1's turn-1 note "next turn I'll submit it" was done in turn 2 and passed). Two fixes found on the way (the approval one was already in the learnings register, lrn-20260824T015238516493Z, and was not searched first): llm_client's default 60 s agent cutoff killed multi-call turns (now `agent_hard_timeout=0`; the kernel's per-turn action limit bounds a turn), and Codex rejects MCP calls under `approval_policy=never` unless the server sets `default_tools_approval_mode = "approve"` (probe2 recorded zero actions until this was set). Runs on the ChatGPT subscription, not the Claude allowance. Bundle excludes `agents/` (per-agent Codex homes hold the kernel token). | `run_bundles/plan25_resident_codex_probe3.tar.gz` |
| `plan25_resident_run1` (4 resident `claude-code/sonnet` agents, 10 turns planned, 4 actions per turn, 40-task bank) | **Stopped at turn 10 by Brian's Claude weekly usage limit** ("You've hit your weekly limit · resets 6am (America/New_York)"); recorded invalid with that reason, no substituted turns. Turns 1-9 (36 agent-turns): one session per agent throughout, 0 built-in tool calls, 148 actions (53 reads, 40 writes, 40 submits, 15 queries; 4 refused over the per-turn limit). **All 40 tasks solved, every submission a first claim, 0 failed hidden tests, 0 wasted duplicates** (vs 28/40, 4 failed, 7 wasted for single-call Luna in shakeout run 1). 8 paid cross-agent reads, 0 transfers; final scrip 198-202 each. Turns took 28-123 s. **Capacity finding:** 4 Sonnet agents × 9 turns hit a Claude weekly limit. It was not the whole plan's allowance: this Claude Max session (Opus) kept working for more than an hour afterwards, so the limit applied to the agents' model/usage class (corrected 2026-10-05 by the session audit). Resident runs now default to Codex/Luna on the ChatGPT subscription. | `run_bundles/plan25_resident_run1.tar.gz` |
| `plan25_resident_probe2` (2 resident `claude-code/sonnet` agents, 2 turns, 2 actions per turn, 8-task bank) | **Passed all four checks.** Same session id every turn per agent; every world change is a `resident_action` kernel receipt from the agent's ae3_action call; 0 built-in tool calls; memory carried over (alpha_1's turn-1 note "next turn I'll write and submit task 28" was carried out in turn 2 and passed the hidden tests). Turns took 32 s and 13 s. Cost source: subscription. A first attempt (`probe1`) failed fast because the new llm_client requires `model_justification` for non-default models; fixed. | `run_bundles/plan25_resident_probe2.tar.gz` |
| `plan25_shakeout_run1` (seed 25001) | **System: clean.** 120/120 decisions committed, all model-selected (`llm_valid`), 0 local failures, 30 decisions per agent, prompt 21-26k tokens, median call 11.6 s, estimated internal charge USD 2.30 (actual USD 0, subscription). **Behavior: mechanical.** Actions were only read (42), write (39), submit (39); 28 of 40 tasks solved (8/7/6/7 per agent), 4 failed hidden tests, 9 paid cross-agent reads, no queries or transfers. **Bug found:** 7 passing submissions earned nothing because the task was already claimed and agents could not see claims; fixed by marking `bounty_claimed_by` on the task statement and in the artifact listing. | `run_bundles/plan25_shakeout_run1.tar.gz` |

## Exact next action

M7 step 2: launch the 16-agent, 40-turn run on the 146-task bank and record it.
