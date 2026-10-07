# View coverage: the three views checked against the model

The model is [`ODD.md`](ODD.md) and [`ae3_model.yaml`](ae3_model.yaml). This
page checks the dashboard's three hand-written views against it, one event type
at a time.

| View | Code |
|---|---|
| **Feed**: Ecosystem tab, the activity list and agent cards | `dashboard/server.py:1232` `_resident_action_rows`, `:1333` `_operator_state` |
| **Matrix**: Interactions tab, the agent-by-agent table | `dashboard/server.py:998` `_agent_graph` |
| **Living view**: World Substrate scene | `viz/world_substrate_view.py:67` `build_projection`, `:310` `build_profile` |

Checked on 2026-10-06 at commit `3a34a78`:

- The views were run on run5 (`plan25_codeflow_run5`: 3,443 events, 16 agents ×
  40 turns).
- Synthetic events were used for the event types run5 never produced: a
  transfer, two messages in a row, a free code read, a solution rewrite and a
  refusal.
- No view code was changed.

**Legend:**

- **shown**: the view shows the event's information.
- **partial**: the event shows up, but without fields that matter.
- **hidden**: left out on purpose, with the reason given.
- **missing**: relevant to the view, not shown, and no reason recorded.

## Table

Rows are the 14 event types a resident run can emit. The other 20 declared
types (`scope: legacy` or `resident_unreachable` in the YAML) cannot occur in a
resident run, so none of the three views needs them. The feed's older
loop-run branch (`server.py:1393-1459`) still shows `loop_decision`.

| Event | run5 count | Feed | Matrix | Living view |
|---|---|---|---|---|
| `resident_action` | 955 | shown: one row per action, refusals included | hidden: not a relation between agents | **missing**: 52 kernel refusals not shown (gap 5) |
| `resident_turn` | 640 | shown: "ended turn t: note" | hidden: not a relation | shown: note bubble at the agent's bench |
| `artifact_read` | 360 | shown: "bought X from Y" when scrip moved, else "read X" | shown: free reads of solutions as "read code" cells; paid task-statement reads as totals per agent | **partial**: paid reads and own-task reads shown; 45 free reads of other agents' code not shown (gap 4) |
| `artifact_written` | 271 | **partial**: "wrote X" from `resident_action`; no create vs rewrite, no type (gap 7) | hidden: not a relation | **partial**: 193 new solutions shown; 78 rewrites not shown (gap 4) |
| `task_bounty_scored` | 267 | shown: passed (paid), passed but already claimed (unpaid), failed (error type) | partial: first claims counted per agent; failures left out because the matrix shows relations | shown: board count, checker passed vs failed-or-unpaid |
| `royalty_paid` | 17 | shown: added to the solver's submit row | shown: "reused helper" cells | shown: message bubble from solver to author, +scrip |
| `kernel_query` | 5 | **partial**: "searched the world", no query type (gap 7) | hidden: not a relation | **missing** (gap 5) |
| `world_initialized` | 1 | hidden: the cards read the final state | hidden | partial: starting scrip is hard-coded to 100, not read from the run (gap 6) |
| `action` | 927 | hidden: duplicate of `resident_action`, and it holds solution text | hidden | hidden |
| `agent_message` | 0 (run6: 0) | shown: each message its own text (gap 2 fixed) | shown: "msg N" cells | shown: speech line from sender to recipient |
| `transfer` | 0 | shown: "paid X N scrip" with the memo (gap 1 fixed) | shown: "paid N" cells, N = scrip sent (gap 1 fixed) | shown: "pays another agent", balances move |
| `resource_transfer` | 0 | partial: "transfer resource" | hidden: `llm_budget` means nothing for Codex agents | hidden: same reason |
| `artifact_deleted` | 0 | partial: "delete artifact" | hidden | **missing**: a deleted helper stops being linked, so the view can mislead (gap 5) |
| `resident_session_changed` | 0 | **missing** (gap 5) | hidden | hidden |

**Shared-project events (Plan 27 M2, 2026-10-06).** Only runs started with
`--aes-pilot` emit these; run5 has none (count = in the scripted fixture runs of
`tests/test_pilot_kernel.py`). Checked by `_check_views` in that test on the
real events of a scripted run, and by eye on the scripted tinydb run in Plan 27's review log.

| Event | Feed | Matrix | Living view |
|---|---|---|---|
| `change_submitted` | shown: folded into the proposer's row, "proposed a change (“note”): …" | hidden: not a relation | hidden: the integrated or rejected frame stands for it |
| `change_integrated` | shown: "… integrated into the shared project as <commit> (files)" | hidden: authorship shows as builds-on and co-built | shown: agent walks to the Project station; station counts integrations |
| `change_rejected` | shown: "… rejected — <reason>", outcome colour failed | hidden | shown: agent walks to the Project; station counts rejections |
| `aes_judged` | shown: row by "AES": "judged <commit> by <agent>: SC-X: insufficient → supported (unchanged: …) [s]" | hidden: not between agents | shown: station's criteria-met count and last judgement |
| `bounty_paid` | shown: payee row "earned N scrip: SC-X met at <commit>, bounty 30 shared with …" (not counted as the payee's action) | shown: "co-built N" cells between payees of one bounty; node label counts bounties | shown: message from the Project to the payee, scrip rises |
| `royalty_paid` (`source: pilot_function_call`) | shown: author row "earned a 3 scrip royalty: <agent>'s change calls its function f (file)" | shown: "builds on N" cells (dashed, orange edge) | shown: message from the caller to the author, scrip rises |

The run5 event counts were made by counting `event_type` over `events.jsonl`.
The view outputs were checked by running the three view functions on the same
log:

| What was compared | Result |
|---|---|
| Feed rows | 1,595 (955 actions + 640 notes) |
| Matrix totals | 45 code reads, 17 reuses, 170 statement reads, 128 solved |
| Living view rules | 1,432 frames |
| Living-view scrip after replaying every frame vs the ledger in the receipt | equal for all 16 agents |

## Gaps

**Fixed on 2026-10-06** (Plan 26, model-gap fixes): gaps 1, 2 and 3, and the
read-price half of gap 8; the task-listing half of gap 8 too. Each is kept
below with what changed, so the evidence for the original finding stays.

1. **Fixed: transfers are now shown** (feed "paid X N scrip"; matrix "paid N";
   test `tests/test_resident_views_joins.py`). Original finding: **Transfers are half-shown.** No run has made a transfer yet, so no view has
   been tested on a real one.
   - Feed: the joins at `server.py:1243-1244` never include `transfer`, so the
     row reads just "transfer" (`server.py:1310`), with no amount, recipient or
     value.
   - Matrix: `_agent_graph` has no `transfer` case (`server.py:1022-1043`), so
     scrip sent from one agent to another never appears as a cell.
   - Living view: shows it (`world_substrate_view.py:169`).
   - Probe: a transfer event of 7 scrip gave the feed row "transfer" with value
     0, and no matrix cell.
2. **Fixed: the kernel logs a per-call `action_id` on `resident_action` and
   `agent_message`, and the feed joins on it** (older logs pair messages in
   order). Original finding: **Repeated messages are mislabelled in the feed.**
   - `send_message` does not advance `event_number` (`resident.py:181-183`,
     `:222-225`), and the feed matches a message to its action by
     `(event_number, principal_id)` (`server.py:1303`).
   - So two messages an agent sends with no kernel action in between both show
     the first message's text and recipient.
   - Probe: messages "first" to alpha_2 and "second" to alpha_3 both rendered as
     "messaged alpha_2: “first”".
3. **Fixed: every view, live or review, reads `VIEW_EVENT_LIMIT` (100,000)
   events.** Original finding: **The live feed sees fewer events than the other views.**
   - The live `/operator-state` reads the last **2,000** events
     (`server.py:1705`). The live matrix and living view read 100,000
     (`server.py:1657`, `:1679`), and review mode reads 100,000 (`server.py:1537`).
   - run5 had 3,443 events, so while it was running the feed's counts and agent
     cards covered only its latest part, while the other two views covered all
     of it.
   - Review mode, which Brian uses after a run, is unaffected.
4. **The living view leaves out two of the model's relations.**
   - Free reads of another agent's code (`artifact_read` with price 0 on a
     solution) fall through both branches at `world_substrate_view.py:153-165`.
     These are 45 in run5, the same 45 the matrix shows as "read code".
   - Rewrites of solutions are skipped (`was_update is not True` at
     `world_substrate_view.py:166`): 78 of 271 writes in run5.
   - Neither omission has a comment giving a reason.
5. **Some resident events reach no view at all.**
   - Kernel refusals: 52 in run5, of which 9 were the per-turn limit, 23 reads
     of artifacts that do not exist, 19 malformed actions and 1 rejected
     submission. They appear only in the feed.
   - `kernel_query` is not in the living view.
   - `artifact_deleted` is not in the living view, although deleting a passing
     helper silently stops royalties for it.
   - `resident_session_changed` is in no view.
6. **Facts the views assume instead of reading from the run.**
   - The living view hard-codes `starting_scrip=100` (`server.py:1682`) rather
     than reading the run's configuration (`config/config.yaml:14`). The two
     agree today, and the replayed balances matched the ledger on run5.
   - Task statements are created without any event
     (`run_recoverable_evaluation.py:640`), so every view gets them from the
     final world state, not from the log.
   - The matrix treats every paid or non-solution read as a "task description"
     read (`server.py:1028-1032`). Once agents read other kinds of artifact,
     those reads will be mislabelled.
7. **The feed drops detail the model has.**
   - Writes do not say whether they create or overwrite, or what type they are
     (`server.py:1281-1282`).
   - Queries do not say what was asked (`server.py:1307-1308`).
8. **Model gaps the views cannot fix.** These show up as empty cells in the
   views but are not view bugs.
   - Fixed: agents can now set read prices (`ae3_action` `read_price`; ODD
     6.3), and the matrix shows paid reads of code as "bought N".
   - Fixed: the observation now lists every unclaimed task and the newest 60
     other artifacts (ODD section 4). Reproduced first: the old 200-row
     listing showed 195 of 365 tasks on the 365-task bank.

A minor point that is not about coverage, fixed with the matrix change: the
matrix script's `\d` inside a normal Python string raised a `SyntaxWarning` on
every import.

## Could World Substrate's living-scene profile be a declared view mapping?

**Partly. It already declares the second half of a view, but not the first.**

A view has two steps:

1. **Projection: events become state.** Example: `artifact_read` with price 2
   moves 2 scrip from buyer to seller and adds 1 to the market's sales.
2. **Presentation: state and steps become pictures.** Example: the buyer walks
   to the market and "buys another agent's work" appears.

The living-scene profile (`world-substrate-living-scene/v1`; contract in
`world-substrate/docs/contracts/living-scene-v1.md`) declares step 2 as data:

- `actors` and `entities` with `bindings`: dotted read paths into entity state,
  for example `scrip → components.member.scrip`;
- `event_visuals` keyed by exact `rule_id`, with move, feedback and transmit
  operations.

It is strict about authority:

- a profile cannot write state;
- a step with no declared visual is shown as a neutral `generic_event` rather
  than guessed.

That makes it a sound target for generating views from the model.

Step 1 is still hand-written Python. `build_projection` (`world_substrate_view.py:147-279`)
decides which AE3 events become which substrate rules and state changes, and
that is exactly where gaps 4-6 live.

**What is missing for the profile to act as a declared view mapping:**

- **A declared event→rule mapping.** For each AE3 event type, the YAML would
  give:
  - an optional condition, for example `read_price_paid > 0 and recipient != principal_id`;
  - the rule id;
  - the state updates as path ← expression.

  It would live in `ae3_model.yaml`, and one generic interpreter would replace
  `build_projection`.
- **Required coverage.** The model's `view_coverage` would be checked against
  that mapping, so every resident event is either mapped or marked hidden with
  a reason. Today a missing mapping is silent: the event is simply never
  projected, so not even `generic_event` appears.
- **Non-scene views.** The feed (rows of text) and the matrix (counts per agent
  pair) are not scenes. The same declared mapping would need two more simple
  renderers: a sentence template per event, and per-pair count edges.
  Otherwise the profile format covers only the living view.
- **Joins.** The feed links several events into one row: an action with its
  checker result and royalties. A declared mapping needs a join key the kernel
  actually guarantees. `event_number` alone is not one (gap 2). A per-action id
  logged on every event an action causes would fix this at the source.

The `view_coverage` block already in `ae3_model.yaml` is the first piece: a
checked declaration of what each view should show. The next step would be the
event→rule mapping for the living view, since its presentation half is already
declared.
