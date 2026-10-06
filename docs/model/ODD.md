# Agent Ecology 3 — model description (ODD protocol)

This is the explicit description of the model that Agent Ecology 3 (AE3) runs
today. It follows the ODD protocol (Overview, Design concepts, Details; Grimm
et al. 2006, updated 2020). It is meant to be the single source of truth that
the dashboard views project. The machine-readable twin is
[`ae3_model.yaml`](ae3_model.yaml). A test keeps its event list identical to
the code (`tests/test_model_declaration.py`). How each view covers each event
is in [`VIEW_COVERAGE.md`](VIEW_COVERAGE.md).

Scope: the **resident ecology** that Plans 25 and 26 run
(`scripts/run_resident_ecology.py`). The kernel also has older paths:
autonomous loop artifacts, the auction mint, and in-world LLM calls. They are
listed in the YAML as `legacy` and are not described here. All line numbers are
as of commit `3a34a78` (2026-10-06).

A running example is used throughout: **Agent 3 and the helper `mex`**. Agent 3
reads its task `CF/123/mex`, writes a solution, tests it in its own folder and
submits it. The checker runs the hidden tests and the solution passes, so Agent 3
earns 10 scrip. Later, Agent 7 submits a solution for `CF/123/answer`, which calls
`mex` without defining it. The checker links Agent 3's passing code in ahead of
Agent 7's. Agent 7 passes and earns 10 scrip, and Agent 3 earns a 3-scrip
royalty.

---

## 1. Purpose and patterns

**Current question:** *is the system set up so agents behave intelligently?*
(Plan 26; Brian, 2026-10-06: "we are just trying to make sure that system is
set up correctly"). **Later question:** *does cooperation pay at scale?* That
needs many agents, long horizons and a real oracle, chosen by Brian (Plan 26 M5).

Patterns we expect to see if the model is right, and the event that shows each
one:

| Pattern | What it looks like | Observed through | Latest evidence |
|---|---|---|---|
| Agents test before submitting | shell commands in the agent's own folder before `submit_to_mint`; few submissions that fail for trivial reasons | `resident_turn.sandboxed_shell_commands`, `task_bounty_scored.reason` | run5: 13-36 shell commands per agent, but 129 of 267 submissions still failed (101 wrong answers) |
| Agents reuse solved helpers | a passing solution calls a helper someone else solved, without redefining it | `royalty_paid` (one per reused helper) | run5: 19 calls to another agent's helper, 17 royalties to 9 authors; run6: 12 |
| Agents trade at posted prices | an agent pays another agent's posted `read_price` for work it values | `artifact_read` with `read_price_paid > 0` and `recipient != principal_id` | run5: 170 paid cross-agent reads, **all of task statements**. No agent can price its own work (see 6.3), so this pattern cannot appear for solutions |
| Royalties follow real calls | a royalty is paid only when the passing code calls the helper and does not redefine it | `royalty_paid` against the solution's code | enforced by `mint.py:400`; run5 had 17 royalties, all from genuine calls |
| Agents talk when it helps | messages that ask for or offer help | `agent_message` | run6: 0 messages in 160 agent-turns (messaging available, mentioned once on turn 1) |

Evidence: [Plan 25 run log](../plans/25_scale_shakeout.md) (run5) and the
[Plan 26 review log](../plans/26_watch_the_ecology.md) (run6).

## 2. Entities, state variables and scales

| Entity | What it is, concretely | Key state | Source |
|---|---|---|---|
| **Agent** | One long-lived Codex session acting as principal `alpha_<n>`. Its memory lives in the resumed session. | `principal_id`, secret `token`, `session_id`, `actions_this_turn`, `inbox`, private `workdir` with a shell, `scrip` (in the Ledger) | `simulation/resident.py:128` |
| **Artifact** | A named piece of text with an owner. Everything agents read, write and submit is an artifact. | `id`, `type`, `owner`, `content`, `read_price`, `access_contract_id`, `metadata`, `deleted` | `world/artifacts.py` |
| **Task statement** | An artifact of type `task_statement`, one per task, owned by the task's owner. Reading another agent's statement costs 2 scrip. | `read_price = 2`, `metadata.plan24_task_id`, `metadata.bounty_claimed_by` | `scripts/run_recoverable_evaluation.py:605`, `:646` |
| **Solution** | An artifact of type `solution:<task id>` whose content is plain Python. | `type` names the task; a Markdown code fence around the code is stripped | `world/mint.py:107-108` |
| **Task** | One CodeFlowBench helper function, for example `CF/123/mex`. | `entry_point`, `prompt` (statement plus one worked example), hidden `test` (two or more literal input/output cases), `requires` (helpers it calls), `claimed_by`, `claimed_artifact` | `world/mint.py:126`, `scripts/build_codeflow_bank.py:82` |
| **Ledger** | Scrip balance per principal. All money moves here. | `scrip` (starts at 100); `llm_budget` (set to 1.0, never spent by Codex agents) | `world/ledger.py`, `config/config.yaml:14`, `scripts/run_resident_ecology.py:43` |
| **Checker** | The mint in `task_bounty` mode plus the hidden-test scorer. | pays `100 // mint_ratio = 10` scrip per first pass; `royalty_scrip = 3`; 10 s timeout | `world/mint.py:304`, `config/config.yaml:84`, `config.py:159`, `:162` |
| **Message** | A free note from one agent to another. | `sender`, `recipient`, `text` (1-1000 characters), `turn` | `simulation/resident.py:141`, `:209` |
| **Kernel** | The shared clock and action endpoint. | `turn`, `actions_per_turn` (default 4), `event_number`, a lock that runs actions one at a time | `simulation/resident.py:144`, `scripts/run_resident_ecology.py:133` |

**Scales.** Time is measured in **turns**. In one turn every agent gets one
Codex call, and in that call it may make up to `actions_per_turn` kernel
actions. Runs so far had 8 or 16 agents and 20 or 40 turns. Within a turn there
is no clock: actions are ordered only by when they reach the kernel. Money is
whole scrip. Space does not exist; "who sees what" is set by artifact access
contracts.

## 3. Process overview and scheduling

```
initialize world (N agents x 100 scrip, checker)  -> world_initialized
seed task bank (one statement per task, no event)
for turn = 1 .. T:                                   scripts/run_resident_ecology.py:102
    all agents start their turn at once              asyncio.gather, :105
        observe (prompt built before any action)     resident.py:444
        Codex call: think, run shell in own folder,  (shell use is free and invisible to the world)
          call ae3_action up to 4 times              resident.py:173 -> resident_action
             each action runs under one lock         resident.py:174
        end of turn: note, counts                    resident.py:494 -> resident_turn
    wait for every agent, then checkpoint receipt    scripts/run_resident_ecology.py:115
```

- **Order within a turn is not fixed.** All agents run at once, and each action
  takes the kernel lock (`resident.py:174`), so actions run in the order they
  arrive. That order depends on model latency. For example, if Agent 3 and
  Agent 9 both submit `mex` in turn 5, whichever submission reaches the lock
  first is paid.
- **Observations are snapshots from the start of the turn.** Each agent's
  prompt is built before its first model call (`resident.py:444`). Coroutines
  run up to their first `await`, so all prompts for a turn are built before any
  action in that turn. Actions during the turn see live state: a `read_artifact`
  returns current content, and a `submit_to_mint` can find the bounty already
  claimed.
- **Failure stops the run.** A failed model call, a missing session id, a
  non-ae3 built-in tool or an error finish raises `ResidentRunError`. The run is
  then recorded as invalid; nothing is substituted (`resident.py:469`, `:477`, `:513`, `:515`).

## 4. Design concepts

**Basic principle.** Agents have no assigned role or strategy
(`resident.py:316`). The only money source is the checker, so any cooperation
has to pay through it: royalties for reused helpers, and read prices for
information.

**Sensing: what an agent sees each turn** (`ResidentKernel.observation`,
`resident.py:230`):

1. On turn 1 only, the rules text (`RESIDENT_RULES`, `resident.py:293`) and the
   workspace note (`:286`). After that the agent relies on its resumed session.
2. `Turn t. You are alpha_3. Your scrip: 112. All scrip balances: {...}`. Every
   agent sees every balance.
3. "Artifacts you can see now": the first **200** readable artifacts in creation
   order (`resident.py:233`), with the agent's own bootstrap artifacts removed
   afterwards (`:237`). Each row gives id, type, owner, read price and, if paid,
   who claimed the bounty. Content is not shown; reading costs an action. Task
   statements are created first, so the list fills with tasks.
   **Consequence (estimated from each run's final artifact order, replicating
   the query filter in `world/queries.py:54-96`):** in run5 (146 tasks) agents
   were shown all 146 tasks and 49 of 193 solutions. In run6 (365 tasks) they
   were shown 195 tasks and **no solutions**. The rest are reachable only
   through `query_kernel` with an offset.
4. "Solved helpers the checker links in automatically": every solved task that
   another task requires, with its function name and author (`resident.py:264`).
5. "Messages to you since your last turn", shown once and then cleared
   (`resident.py:256`).

**Interaction.** Agents interact only through the kernel:

- paying to read another agent's artifact (`artifact_read`);
- calling another agent's solved helper, which earns that agent a royalty
  (`royalty_paid`);
- transferring scrip (`transfer`);
- sending messages (`agent_message`).

There is no negotiation step: prices are posted and royalties are automatic.

**Stochasticity.** The model's choices are the main source of randomness. Turn
order within a turn depends on latency (section 3). The task bank is built with
a seeded shuffle (`build_codeflow_bank.py:89`), so the same seed gives the same
bank. The checker is deterministic apart from its 10 s timeout.

**Observation (what we record).** One append-only `events.jsonl` per run
(`world/logger.py:52`). It has 34 declared event types, 14 of which can occur in
a resident run. There is also a `run_receipt.json` holding the final world state
(`scripts/run_resident_ecology.py:56`). The three views read only these two
files. They never infer activity from prompts.

**Adaptation, learning, prediction.** Each agent keeps memory in its resumed
Codex session and writes an end-of-turn note to itself (`resident.py:297`). No
learning is coded into the kernel.

**Collectives.** None are declared. Any grouping would have to emerge from
messages or reuse.

## 5. Initialization and input data

**Initialization** (`scripts/run_resident_ecology.py:40-53`, `world/world.py:343`):

- N principals `alpha_1..alpha_N`, each with 100 scrip, an `llm_budget` of 1.0
  and a 250,000-byte disk quota.
- Mint mode `task_bounty`, cross-principal trading on.
- Bootstrap artifacts per agent. These are leftovers from the loop design,
  hidden from the observation: `agent_profile`, `strategy`, `state` and
  `notebook` (self-owned), and an `agent_loop` (private). The world also has 4
  private kernel services.
- One task statement per task, owned by the task's owner, read price 2
  (`run_recoverable_evaluation.py:605-655`). These are written straight into the
  store, so **no event records their creation**.
- `world_initialized` is logged (`world/world.py:326`).

**Input data: the local CodeFlowBench bank.** `scripts/build_codeflow_bank.py`
downloads CodeFlowBench (MIT; Codeforces problems split into helper functions
with declared dependencies). It keeps problems that have at least 3 helpers,
some depending on others, and helpers with at least 2 literal test cases. It
assigns task owners round-robin and writes a JSONL bank to
`~/.cache/agent_ecology3/`. The bank is **never committed**: redistribution
terms for the Codeforces-derived text are unverified (`build_codeflow_bank.py:8-10`).
Each task's prompt adds one worked example, which is also one of the hidden
cases (`build_codeflow_bank.py:55`). Run sizes so far: run5 146 tasks from 40
problems; run6 365 tasks.

## 6. Submodels

Each rule below is the exact behaviour in code. "Counts as an action" means it
uses one of the agent's per-turn actions.

### 6.1 Per-turn action limit (`resident.py:173-207`)

- At turn start `actions_this_turn = 0` (`resident.py:443`).
- Each `ae3_action` call first checks `actions_this_turn >= actions_per_turn`
  (default 4). If it is, the call is refused with `turn_action_limit` and
  nothing runs.
- Otherwise the counter goes up by one **before** the action runs, so a refused
  or failed action still uses up an action.
- Every call, refused or not, is logged as `resident_action`.
- Shell commands in the agent's own folder are free and unlimited, and do not
  touch the world.

Example: Agent 3 reads, writes, submits and then reads again (4 actions). A
fifth call in the same turn is refused (`turn_action_limit`). In run5, 9
actions were refused this way, out of 52 refusals in total.

### 6.2 read_artifact (`action_executor.py:145-197`)

1. The artifact must exist and not be deleted (`not_found`).
2. The contract must allow reading. Freeware allows anyone (`contracts.py:93`).
3. If `read_price > 0`, the reader must be able to afford it
   (`insufficient_funds`). Then the price moves from reader to owner, **unless
   the reader is the owner, when nothing moves** (`:170-180`).
4. The full content is returned. `artifact_read` is logged with
   `read_price_paid` set to the posted price, even when nothing moved.

Example: Agent 7 reads `alpha_3_task_123_mex` and pays 2 scrip to Agent 3.
Agent 3 reading its own statement pays nothing, but the event still says
`read_price_paid: 2`. In run5, 145 of the 315 task-statement reads were own reads.

### 6.3 write_artifact (`action_executor.py:199-296`)

1. The id must not be deleted or kernel-protected. Overwriting needs write
   permission; freeware allows only the writer.
2. Growth must fit the 250,000-byte disk quota (`quota_exceeded`).
3. The artifact is created or overwritten, and `artifact_written` is logged
   with `was_update`.
4. **Price:** the kernel reads `read_price` from the top level of the payload
   (`actions.py:634`). The agents' only tool, `ae3_action`
   (`mcp/loop_action_server.py:66`), has no `read_price` field, so every
   agent-written artifact has read price 0. The rules nevertheless tell agents
   "You may set read_price on your own artifacts" (`resident.py:308-309`). In
   run5 and run6 all 319 agent-written solutions had read price 0. **Reading
   another agent's code is therefore always free, and selling work at a posted
   price is impossible for agents.**

### 6.4 submit_to_mint and the checker (`world/mint.py:304-358`)

1. The artifact must exist, the bid must be at least 1 and affordable, and the
   submitter must own or have written the artifact (`invalid_submission`). The
   bid is checked but **not taken**.
2. The task is named by the artifact type `solution:<task id>`, matched without
   regard to case (`mint.py:174`).
3. **Linking** (`mint.py:360-385`). The checker takes the task's declared
   `requires` plus any helper of the same problem whose function name the
   solution calls. For each one that is already solved and not deleted, it puts
   the passing code first (the "prelude").
4. **Check** (`mint.py:183-221`). It runs
   `prelude + solution + hidden test + check(entry_point)` in a fresh isolated
   Python with a 10 s limit. Exit code 0 means score 100; anything else means
   score 0, with the last error line as the reason.
5. **Pay** (`mint.py:331-343`). Only the **first** passing submission per task
   is paid: `100 // 10 = 10` scrip, newly created. The task is marked claimed,
   and `bounty_claimed_by` is written onto its statement. A later pass earns 0
   ("already claimed").
6. `task_bounty_scored` is logged with `passed`, `first_claim`, `scrip_minted`
   and `reason`.

### 6.5 Royalty (`world/mint.py:387-413`)

- This runs only after a **first-claim pass**.
- For each linked helper, the helper's author is credited `royalty_scrip = 3`
  scrip (newly created; the solver pays nothing) when all of these hold:
  - the author is not the solver;
  - the passing solution **calls** the helper by name;
  - the passing solution does **not define** a function with that name
    (`mint.py:400`).
- One `royalty_paid` is logged per helper. Its `principal_id` is the author; its
  `solver` is the agent who reused the helper.

Example: Agent 7's `answer` calls `mex` → Agent 3 gets +3. If Agent 7 had
pasted its own `def mex`, Agent 3 would get nothing.

### 6.6 transfer (`action_executor.py:751-777`)

- Trading must be on (`trading_disabled`).
- The amount must be a positive whole number. Both sides must be principals,
  and the sender must be able to afford it.
- The scrip moves, and `transfer` is logged with sender, recipient, amount and
  memo.
- run5 and run6: 0 transfers.

### 6.7 query_kernel (`action_executor.py:690-705`, `world/queries.py:25`)

- A read-only query by `query_type`: `artifacts` (filters, `limit`, `offset`),
  `artifact`, `principals`, `balances`, `mint`, `events`, `libraries`,
  `dependencies` and others.
- Free in scrip; counts as an action.
- `kernel_query` is logged only on success.
- run5: 5 queries.

### 6.8 send_message (`resident.py:209-228`)

- Handled by the resident kernel, not the world.
- The recipient must be another existing agent (`invalid_recipient`). The text
  must be non-empty (`empty_message`) and at most 1000 characters
  (`message_too_long`).
- The message is appended to the recipient's inbox and appears in its **next**
  observation (section 4). A message sent during turn t is read at turn t+1
  because all turn-t prompts were already built.
- Free in scrip; counts as an action; does **not** advance `event_number`.
- `agent_message` is logged with the full text.

### 6.9 Other actions resident agents can reach

| Action | What it does |
|---|---|
| `delete_artifact` | Soft-delete (`action_executor.py:664`). A deleted passing solution is no longer linked for later tasks. |
| `transfer_resource` | Move `llm_budget` to another principal (`:779`). Meaningless for Codex agents. |
| `subscribe_artifact`, `unsubscribe_artifact`, `noop` | Bookkeeping only. |

`edit_artifact`, `invoke_artifact`, `update_metadata` and `mint` exist in the
kernel, but the tool cannot supply their required fields (`actions.py:678-780`).
In run5 all 8 `edit_artifact` attempts were refused as `invalid_action`.

### 6.10 What every action records

- `resident_action` for every call: turn, agent, action type, artifact,
  success, error code.
- `action` for every parsed kernel action. It holds the full intent, including
  solution text, so it must never be published.
- One specific event per successful action (sections 6.2-6.8).

Two things advance or skip `event_number` differently:

- Parse failures (`invalid_action`) and turn-limit refusals do not advance it
  and produce no `action` event.
- In run5 there were 955 `resident_action` events and 927 `action` events. The
  difference of 28 is 9 turn-limit refusals plus 19 parse failures.
