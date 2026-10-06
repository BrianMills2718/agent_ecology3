---
plan_id: "agent-ecology3#26"
dependencies: ["agent-ecology3#25"]
dependencies_reviewed: "2026-10-06"
---
# Plan #26: Watch the Ecology — Feed, Graph, Messaging, Public Replay

**Status:** 🚧 In Progress — M3 active (agents can message each other)
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
**Last outcome-bearing update:** 2026-10-06, defects exposed by the system
model fixed (read prices, transfers, message join, live feed window, task
listing).

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
- Dense agent-to-agent relations are shown as a matrix (rows used the work
  of columns), not a node-link graph: the shared viewer (typed-graph/v1) was
  tried on run5 and its layered layout drew 50 crossing wires among 16
  agents with unreadable labels. The `/agent-graph` payload stays
  typed-graph/v1 so a sparse view can reuse the shared viewer later; no
  per-project graph renderer is built.
- Messages go through the kernel like every other action: authenticated by
  the agent's launch token, recorded as an event, delivered in the recipient's
  next observation.
- Public pages contain no CodeFlowBench task/solution text, no keys, no Codex
  folders; checked by `scripts/run_evidence.py`-style leak checks before publish.

| Capability | Canonical seam | State | Evidence |
|---|---|---|---|
| Activity feed | `dashboard/server.py` `_resident_action_rows` | working: 1,595 run5 events in plain words; totals match `run_evidence.py report` (128 solved, 129 failed, 10 unpaid, 17 royalties); 52 kernel refusals shown; transfers as "paid X N scrip"; live mode reads 100,000 events like review | M1 PR; model-gap PR |
| Interactions view | `dashboard/server.py` `/agent-graph`, matrix in the Interactions tab | working: 16×16 matrix of code reads, code bought, helper reuse (orange edge), messages and "paid N" transfers; click or hover any cell or name for a plain-words explanation | M2 PR; model-gap PR |
| Posted prices for agent work | `mcp/loop_action_server.py` `read_price` → `write_artifact` | working, unused so far: an agent sets `read_price` on its artifact; a rewrite keeps it; another agent's read pays it | model-gap PR |
| Turn observation | `simulation/resident.py` `observation` | every unclaimed task id by read price, newest 60 other artifacts, paging hint | model-gap PR |
| Living view | `viz/world_substrate_view.py` | working; agents at one place hide each other | Plan 25 M8, world-substrate#106 |
| Agent messaging | `simulation/resident.py` `_send_message` | working: `send_message` delivers a free note at the start of the recipient's next turn; unused in run6 (0 messages) | M3 PR |

## Model

The model the views project is written down in [docs/model/ODD.md](../model/ODD.md)
(ODD protocol) and [docs/model/ae3_model.yaml](../model/ae3_model.yaml)
(entities, processes, events; `tests/test_model_declaration.py` keeps its event
list equal to the code). [docs/model/VIEW_COVERAGE.md](../model/VIEW_COVERAGE.md)
checks the feed, matrix and Living view against it and lists the gaps
(2026-10-06). Fixed the same day (Brian approved): agents can set read prices
through `ae3_action`; transfers show as "paid X N scrip" in the feed and
"paid N" in the matrix; each message keeps its own text (per-action id);
every view reads the same 100,000-event window; and the turn observation lists
every unclaimed task (it showed 195 of 365). Still open: free code reads and
solution rewrites absent from the Living view, and the other gaps in that page.

## Milestones

| Milestone | Planning state | Output | Review point |
|---|---|---|---|
| M1 Activity feed for resident runs | done (awaiting Brian's look) | plain-words feed from resident events; agent cards without the meaningless budget | run5 at localhost, press Play |
| M2 Agents-only interaction view | done (awaiting Brian's look) | shared graph viewer; agents as nodes; bought / reused (royalty) / messaged edges weighted by count; click an agent for its tasks | run5 Interactions tab |
| M3 Agents can message each other | built; unused in first run (awaiting Brian on a per-turn reminder) | `send_message` action; inbox in the recipient's next observation; shown in feed, graph, Living view; 8 agents × 20 turns | live run link |
| M4 Public read-only replay | conditional (after M1-M3) | static replay of one finished run on brianmills.dev after a privacy check | public URL |
| M5 Real oracle | human_decision_required | Brian chooses what agents get paid for | Brian's choice |

## Active slice: M3 — agents can message each other

**Visible result:** in an 8-agent run, messages between agents appear in the
feed ("Agent 3 → Agent 5: …"), as "msg N" in the Interactions matrix, and as
speech between agents in the Living view.

**Steps:**
1. Kernel action `send_message(recipient, text)`: validated recipient, text
   capped in length, counts as one action, recorded as an `agent_message`
   event; free (no scrip) so it is a pure communication channel.
2. The recipient's next observation lists messages received since its last
   turn (sender, text); the resident rules mention the action once.
3. Feed rows and matrix counts for `agent_message` (the matrix already counts
   them); Living view shows a message as an `information.transmit` from
   sender to recipient.
4. Tests without model calls; then 8 agents × 20 turns on the 365-task bank
   as a systemd unit; record messages sent, replies, and what they were about.

**Focused check:** a message sent in turn t appears in the recipient's turn
t+1 observation and in all three views.

**Failure / containment:** unknown recipient or empty text is refused with a
reason, like any invalid action.

## Decisions and assumptions

| Choice | Disposition | Reason / evidence |
|---|---|---|
| Watchability before oracle work | human_set (Brian, 2026-10-06) | quotes above |
| Web look-ups are a legitimate agent strategy | human_set (Brian, 2026-10-06: "i would consider that a legiimate strategy") | 4 agents searched for editorials in run5 |
| UI fixes before messaging | agent_decided_reversible | so the first messaging run is watchable |
| Matrix, not node-link graph, for agent-to-agent relations | agent_decided_reversible | shared graph viewer tried first (workspace rule); dense relations (37 code-read and 13 reuse pairs among 16 agents) were unreadable as a layered graph; payload kept typed-graph/v1 |

## Human decisions

- **M5:** which real oracle the agents work for. Not needed until M1-M4 are
  done.

## Review log

| Date | Milestone | What Brian can open | Result |
|---|---|---|---|
| 2026-10-06 | model-gap fixes | run5 (review mode) and a provider-free live kernel fixture with priced code, two messages in one turn, two transfers and 2,417 events | fixed five defects the system model exposed, each with a test that makes no model calls: (1) the tool had no `read_price` field although the rules offered it; added, and a rewrite now keeps the price; (2) transfers: feed "paid X N scrip", matrix "paid N"; (3) two messages in one turn showed the first text twice; the kernel now logs a per-action id on both events; (4) the live feed read the last 2,000 events; now 100,000 like the other views; (5) reproduced on the 365-task bank: the observation listed 195 of 365 tasks and no solutions; it now lists every unclaimed task (about 12,000 characters, down from 16,400) and the newest 60 other artifacts. Browser: run5 unchanged (1,595 feed rows; 256 matrix controls, all with tooltips); fixture showed 806 of 806 actions live and paid/bought/msg cells with tooltips |
| 2026-10-06 | M3 | run `plan26_messages_run6` (8 Codex agents × 20 turns, 365-task bank, messaging available): http://localhost:9100/ while it served | 160/160 turns; 110/365 solved; 32 failed (wrong answer 24, NameError 6, wrong argument count 1, other 1); 15-26 shell commands per agent; another agent's helper called 12 times, rewritten 1; 12 royalties to all 8 agents; **0 messages and 0 transfers**. The rules mention send_message once, on turn 1 only; no agent's recorded thinking mentions it (weak evidence: low-effort reasoning is mostly unrecorded). Trading today is posted prices plus automatic royalties, no negotiation. Bundle `run_bundles/plan26_messages_run6.tar.gz` |
| 2026-10-06 | M2 | http://localhost:9097/ → Interactions | built and browser-checked: 16×16 matrix; 256 cells and names hover-checked, all show a tooltip. Found while building: all 170 paid cross-agent reads were task descriptions; reading another agent's code was free (45 times) |
| 2026-10-06 | M1 | http://localhost:9097/ (run5, Ecosystem tab, press Play) | built and browser-checked; awaiting Brian's look. Found while building: 52 actions refused by the kernel (9 for exceeding 4 per turn, 23 reads of missing artifacts, 19 malformed, 1 rejected submission); joining results by event number alone mislabelled 9 of them (fixed by matching agent and artifact) |

## Exact next action

Agents can now price their work and see every open task; the next 8-agent run
is the first that can show priced code, payments and a full task view.
Waiting on Brian (proposed 2026-10-06): add a one-line per-turn reminder that
agents can message anyone, keep each agent's recent messages in its turn
summary, and rerun 8 agents × 20 turns to see whether messaging gets used.
Otherwise continue with M4 (public replay).
