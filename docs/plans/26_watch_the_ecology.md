---
plan_id: "agent-ecology3#26"
dependencies: ["agent-ecology3#25"]
dependencies_reviewed: "2026-10-06"
---
# Plan #26: Watch the Ecology — Feed, Graph, Messaging, Public Replay

**Status:** 🚧 In Progress — M2 active (agents-only interaction graph)
**Type:** durable living plan (company-planning `durable_solo`)
**Priority:** Critical
**Blocked By:** None
**Blocks:** choosing a real oracle (deferred, Brian's call)

**Authority:** Brian, 2026-10-06: "where are we at on a ui? where i can see them
trading and communicating and building and submitting etc"; "we should not be
building ways to make this oracle relevant we are just trying to make sure that
system is set up correctly"; approved this sequence: "ok make this company
plannign compliant an dproceed". This plan owns its milestones, active slice
and review log; [the roadmap](../MVP_ROADMAP.md) owns outcome and priority;
[Plan 25](25_scale_shakeout.md) keeps the run log for scale runs.
**Planning path:** `durable_solo` — one writer, continues across sessions, no
parallel lanes. One shared contract changes (a new kernel action,
`send_message`, in M3); its owner is this repo.
**Selected controls:** continuity = this file; coordination = single lane;
reversibility = git-revertible PRs merged after `make check`; external effect =
M4 publishes a static replay on brianmills.dev only after a privacy check;
data = no CodeFlowBench task/solution text, keys or Codex folders leave the
machine.
**Artifact consumer / decision value:** Brian watches agents trade,
communicate, build and submit, and judges whether the system is set up
correctly before choosing a real oracle.
**Stage / investment boundary:** local prototype plus one public read-only
replay; no oracle work, no verdicts or benchmarks.
**Last outcome-bearing update:** 2026-10-06, plan created.

## Outcome and boundaries

**Outcome:** For Brian, change "a dashboard whose feed is empty and whose graph
is a tangle for long-lived-agent runs, with no way for agents to talk" into
"one dashboard where every trade, message, solution and submission is visible
in plain words, a readable who-works-with-whom graph, agents that can message
each other, and a public replay link".

**Canonical probe:** open a resident run in the dashboard (`run_recoverable_
evaluation.py review --data-dir <run> --port <p>`), press Play: the feed lists
each resident action in plain words with the code it touched; the
Interactions tab shows one node per agent with bought/reused/messaged
edges; in an 8-agent run with messaging, at least one message appears in
the feed, the graph and the Living view. Negative case: an empty or
unsupported run says so instead of showing "Decision 0 of 0".

**Review points (each a clickable UI):** M1 feed on run5; M2 graph on run5;
M3 live 8-agent run with messages; M4 public URL.

**Non-goals:** making the CodeFlowBench oracle stricter (web look-ups are a
legitimate strategy with a real oracle; leaked tests, small tasks and shallow
dependencies are properties of this stand-in oracle); new oracle work;
renderer changes inside World Substrate (issue #106 stays with its owner).

**Authority limits:** deleting run data needs Brian's yes; the public replay
is published only after the privacy check passes.

## Architecture and capability invariants

- The dashboard projects the kernel's own events (`resident_action`,
  `artifact_read`, `artifact_written`, `task_bounty_scored`, `royalty_paid`,
  and M3's message events); it never infers activity from prompts.
- Graphs use the shared viewer (`representation-router/graph-viewer`,
  typed-graph/v1, vendored pinned `dist/graph-viewer.js`), not a per-project
  Cytoscape view.
- Messages go through the kernel like every other action: authenticated by
  the agent's launch token, recorded as an event, delivered in the recipient's
  next observation.
- Public pages contain no CodeFlowBench task/solution text, no keys, no Codex
  folders; checked by `scripts/run_evidence.py`-style leak checks before publish.

| Capability | Canonical seam | State | Evidence |
|---|---|---|---|
| Activity feed | `dashboard/server.py` `_resident_action_rows` | working: 1,595 run5 events in plain words; totals match `run_evidence.py report` (128 solved, 129 failed, 10 unpaid, 17 royalties); 52 kernel refusals shown | M1 PR |
| Interactions graph | `dashboard/server.py` `/interaction-graph`, Cytoscape | unreadable at 16 agents (agents + ~150 task nodes) | run5 screenshot 2026-10-06 |
| Living view | `viz/world_substrate_view.py` | working; agents at one place hide each other | Plan 25 M8, world-substrate#106 |
| Agent messaging | kernel actions | absent: no action sends a message to another agent; turn notes are not shown to other agents | `world/actions.py` `ActionType` |

## Milestones

| Milestone | Planning state | Output | Review point |
|---|---|---|---|
| M1 Activity feed for resident runs | done (awaiting Brian's look) | plain-words feed from resident events; agent cards without the meaningless budget | run5 at localhost, press Play |
| M2 Agents-only interaction graph | fully_specifiable_now (active) | shared graph viewer; agents as nodes; bought / reused (royalty) / messaged edges weighted by count; click an agent for its tasks | run5 Interactions tab |
| M3 Agents can message each other | fully_specifiable_now | `send_message` action; inbox in the recipient's next observation; shown in feed, graph, Living view; 8 agents × 20 turns | live run link |
| M4 Public read-only replay | conditional (after M1-M3) | static replay of one finished run on brianmills.dev after a privacy check | public URL |
| M5 Real oracle | human_decision_required | Brian chooses what agents get paid for | Brian's choice |

## Active slice: M2 — agents-only interaction graph

**Visible result:** the Interactions tab on run5 shows 16 agent nodes; arrows
for "bought from" (paid reads), "reused helper of" (royalties) and later
"messaged"; thicker for more; clicking an agent lists its tasks and trades.

**Steps:**
1. Vendor a pinned `representation-router/graph-viewer/dist/graph-viewer.js`
   and read its typed-graph/v1 contract.
2. Build a typed-graph/v1 document from kernel events (agents as nodes;
   edges aggregated by kind and count); replace the Cytoscape view.
3. Test the projection without model calls; browser-check run5, hovering
   every control for a visible tooltip.

**Focused check:** edge totals equal the feed's counts (paid reads between
different agents; 17 royalties).

**Failure / containment:** if the shared viewer cannot express weighted
edges, extend it in representation-router rather than hand-rolling here.

## Decisions and assumptions

| Choice | Disposition | Reason / evidence |
|---|---|---|
| Watchability before oracle work | human_set (Brian, 2026-10-06) | quotes above |
| Web look-ups are a legitimate agent strategy | human_set (Brian, 2026-10-06: "i would consider that a legiimate strategy") | 4 agents searched for editorials in run5 |
| UI fixes before messaging | agent_decided_reversible | so the first messaging run is watchable |
| Reuse the shared graph viewer | agent_decided_reversible | workspace rule: no per-project graph UIs |

## Human decisions

- **M5:** which real oracle the agents work for. Not needed until M1-M4 are
  done.

## Review log

| Date | Milestone | What Brian can open | Result |
|---|---|---|---|
| 2026-10-06 | M1 | http://localhost:9097/ (run5, Ecosystem tab, press Play) | built and browser-checked; awaiting Brian's look. Found while building: 52 actions refused for exceeding 4 per turn; joining results by event number alone mislabelled 9 of them (fixed by matching agent and artifact) |

## Exact next action

M2 step 1: vendor the shared graph viewer and map run5's agent-to-agent
trades and royalties into typed-graph/v1.
