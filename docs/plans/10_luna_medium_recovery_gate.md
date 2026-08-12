# Plan #10: Luna Medium Compatibility and Recovery Gate

**Status:** In progress — Slices A-E passed; WU-10-05 completion review
**Type:** implementation
**Priority:** High
**Blocked By:** None
**Blocks:** Luna-specific qualification and scarcity calibration (Plan #11)

### Current execution frontier (2026-08-12)

- **Outcome:** run the smallest recoverable, detached, dashboard-visible Luna
  PoC without reopening the accepted model, route, action, or UI architecture.
- **Completed unit:** `WU-10-04`; the separately authorized canary passed on its
  only dispatch from pushed source revision
  `d65b46e0884c98574cd9fd13355c6bd74377e276`.
- **Proven:** exact `codex/gpt-5.6-luna` at medium effort through direct CLI,
  subscription-included billing, one strict `query_kernel` action, passive
  `agent_message` event custody, and caller/readback equality.
- **Next action:** use the canary's observed 7.7-second latency and 15,568-token
  usage to bound one recoverable dashboard-visible PoC unit implementing the
  conditional Slices D-E.
- **Stop condition:** no multi-call Luna run begins until recovery prevents a
  settled or ambiguous attempt from being replaced after interruption.
- **Evidence:** `docs/evaluations/evidence/plan10_luna_recovery_gate/`.
- **Non-claim:** the canary establishes route compatibility only; it does not
  establish reliability, behavioral effect, or valid scarcity parameters.

### Recoverable dashboard PoC checkpoint (2026-08-12)

`WU-10-05` is the active bounded integration unit. Its provider-free vertical
is implemented and frozen before the two-call authentic boundary:

- an atomic Pydantic checkpoint records stable run/attempt identities,
  semantic request hashes, dispatch count, syscall result, trace, and the
  `dispatching -> provider_settled -> applying -> committed` boundary;
- restart rebuilds the deterministic `World`, reapplies the cached settlement
  accounting, and replays the retained response through the normal generated
  loop and kernel action seam rather than making a replacement call;
- measured local CPU jitter is removed from the recoverable model prompt so it
  cannot create false replay drift; the actual dashboard resource state remains
  unchanged and visible;
- dispatch ambiguity, corrupt custody, request/trace drift, or interruption
  during action application becomes terminal `invalid` and raises past the
  loop's ordinary fallback behavior;
- the canonical 16-attempt fixture interrupts after attempt 8 settlement,
  restarts, and ends with exactly 16 provider dispatches and 16 committed
  attempts; and
- `scripts/run_recoverable_evaluation.py` owns detached `start`, `status`,
  `resume`, `pause`, `stop`, and `shutdown` around the existing runner and
  dashboard. Start is paused, requires exact acknowledgement
  `plan10/luna-medium/dashboard-poc/v1`, and is frozen to two attempts.

The authentic run must start only from a clean pushed AE3 revision and the
exact clean accepted shared client. It uses `codex/gpt-5.6-luna`, medium
reasoning, CLI transport, read-only sandbox, isolated home,
subscription-included billing, zero retries/fallbacks, and no MCP server.

The bounded authentic run passed from pushed revision
`3f175e71b08757fd5e298fb85f8d09048899a0d1`:

- exactly two Luna Medium provider dispatches produced exactly two committed
  attempts with no retry, fallback, MCP server, ambiguity, or terminal error;
- both returned the strict `query_kernel`/`artifacts` action with
  `readable_only=true`, both actions succeeded, and both retained only the
  passive `agent_message` Codex event;
- the attempts used 15,576 and 15,739 tokens and completed in 8.52 and 7.23
  seconds; provider cost was USD 0.00 under subscription-included billing and
  AE3 retained separate internal estimated charges of 0.003873 and 0.004149;
- the fresh browser observed the paused `0/2` state and completed `2/2` state,
  preserved Resume/Pause/Stop, showed both loop actions, and reported no
  console errors or failed requests; and
- the compact durable receipt is `dashboard_poc.json`. The external full
  receipt and checkpoint are content-addressed there for local forensic use.

This completes the PoC implementation and evidence boundary only. It does not
qualify reliability, behavioral effect, scarcity parameters, Evaluation 08,
or adoption of AE2's fuller dashboard.

#### Existing dashboard continuity contract

| Entry point | State | Preserved or extended surfaces |
| --- | --- | --- |
| `/` direct load or refresh | paused | Existing state/events panes and resume/pause/stop controls; add stable run, attempt progress, and custody status pills |
| `/` | running | Same panes and controls update through existing 1.5-second polling; actions, events, balances, quotas, and budget remain visible |
| `/` | completed, stopped, or invalid | Reviewable final state/events and stable run/custody identity remain visible; no result is silently presented as running |
| `/state`, `/events` | all states | Existing response remains additive; `recovery` is the only new top-level projection |

No navigation, projection, control, or lifecycle state is removed. A fresh
browser observation of paused -> running -> completed plus console, failed
request, and backend-log inspection remains required at the authentic boundary.

### Slice C checkpoint (2026-08-12)

The one authentic canary passed with exactly one provider dispatch and no
retry, repair, fallback, or MCP server. The retained receipt records:

- stable trace `ae3/plan10_luna_medium_canary_v1/event_0/payer/alpha_1`;
- exact AE3 source `d65b46e0884c98574cd9fd13355c6bd74377e276`
  and shared-client source
  `286715784f1d535d6dfcd2c867ca678d666e27d5`;
- 15,422 prompt tokens, 146 completion tokens, 15,568 total tokens, and
  7.7 seconds observed latency;
- provider cost USD 0.00 under `subscription_included` billing, with AE3's
  configured internal estimated-budget charge retained separately;
- one passive `agent_message` Codex event and no intrinsic/MCP tool execution;
- one Pydantic-validated `query_kernel` action requesting readable artifacts;
  and
- exact caller/shared-client readback equality plus one terminal shared-client
  receipt.

The evidence file is `live_canary.json`, SHA-256
`698faab71cad8f96f1d37231e41703439fe0500c402ec5d96413bc5321518ba0`.
This selects Slices D-E before any multi-call Luna execution.

### Slice A checkpoint (2026-08-12)

The AE3-owned portion of Slice A is implemented and provider-free verified:

- `LunaLoopDecisionV1` is a strict, versioned six-variant action envelope. The
  shared Codex projector produces a closed provider schema with digest
  `4f8344df4e01d3f7adf1287ffe794edeb2552f94e8d8268558d3cc102be5d2d2`.
- The production loop can consume the validated `structured_action` directly,
  while retaining the shared-client result content as the original envelope.
- The exact Luna route is typed and fail-closed: direct CLI, medium effort,
  read-only empty temporary workspace, no retries/fallbacks, isolated Codex
  home, subscription billing, and neither `tools` nor `mcp_servers`.
- The provider-free command/home/prompt/schema inventory is retained at
  `docs/evaluations/evidence/plan10_luna_recovery_gate/slice_a_preflight.json`.

The original Slice A preflight stopped at reviewed shared-client revision
`e068430c991fd460c73d7f4faf5c92ee393b8a66` because intrinsic Codex events were
not public. That blocker is now resolved. Against accepted revision
`286715784f1d535d6dfcd2c867ca678d666e27d5`, the provider-free probe observes
`command_execution`, `file_change`, `web_search`, and `mcp_tool_call` in stream
order through `LLMCallResult.codex_events`, while the existing `tool_calls`
projection remains MCP-only. The retained preflight passes without a provider
call or MCP server.

### Shared dependency resolution (2026-08-12)

`llm_client` Plan #355 implemented the additive public
`LLMCallResult.codex_events` contract in merge
`63f471347f2f1e18b37cf82d50b5546336b6a5e1`. Its machine-readable work graph
accepts the shared unit and advances the downstream Agent Ecology unit to
ready in merge `286715784f1d535d6dfcd2c867ca678d666e27d5`.

AE3 reran the retained preflight against that exact accepted revision through
repo-local unit `WU-10-02`. The unit is implemented and its evidence is under
`docs/evaluations/evidence/plan10_luna_recovery_gate/`. This completes Slice A
only; it does not authorize a Luna call.

The subsequent general audit found that the runtime refunded a returned Luna
call when its action/profile was rejected, accepted unclassified Codex event
types, and checked only for the presence of the shared `codex_events` field
rather than the exact reviewed dependency revision. The user approved the
recommended PoC correction on 2026-08-12: close those one-call safety gaps
before the canary, then require the full recoverable cell and detached worker
only before multi-call scale. Slice B below is that provider-free boundary.

### Slice B checkpoint (2026-08-12)

The canary-safety boundary is implemented in PR #18, merge
`1ac43ad685418e0a5230e935d11d890b7a6c6f0d`:

- production Luna preflight requires the clean imported `llm_client` source at
  exact accepted revision `286715784f1d535d6dfcd2c867ca678d666e27d5`
  before reserving resources;
- returned-but-rejected Luna results settle observed tokens/billing and retain
  a `provider_settled_rejected` receipt instead of refunding the call;
- exceptions after entering the shared-client boundary retain the conservative
  reservation as `dispatch_ambiguous`, with no retry; and
- Codex event custody accepts only `reasoning` and `agent_message`; missing,
  active, malformed, and unclassified event types fail closed after settlement.

All 101 repository tests pass; changed-module mypy and focused lint checks pass.
No provider call was made. Slice C is now the next boundary and still requires
the user's separate exact one-call authorization.

---

## Adopted Direction

The user selected Luna Medium and accepted the staged Plan 10-12 direction on
2026-08-12. This plan is the implementation-ready translation of the first
stage. Reversible technical details use the recommended path below. A change of
model, route, account/billing mode, call count, or success boundary returns to
the user rather than proceeding implicitly.

On 2026-08-12 the user delegated the MVP action-transport choice. The reviewed
decision is to use strict structured output for Luna and leave AE3's existing
MCP bridge unchanged for routes that already use it. Luna receives one complete
decision snapshot and returns one action; it does not need mid-turn reads or
callbacks. MCP would therefore add a server process, a second schema, and a
tool-call parser without adding an MVP capability. Reconsider MCP for Luna only
if a later outcome requires interactive observation or multiple actions inside
one model turn.

**Planning route:** durable solo. Work remains sequential. The shared-client
blocker introduced one real cross-project seam, so Plan #355 used a two-unit
work graph and AE3 uses its repo-local graph as the claim-registry binding. The
graph does not introduce a parallel execution lane.

**Delivery profile:** prototype instrument with runtime-state, LLM, exploratory,
and repository-governance overlays. This plan proves a route and a recoverable
cell; it does not promote AE3 to an operational service or execute a behavioral
evaluation.

---

## Gap

**Current:** AE3's LLM configuration cannot select a structured decision call
or express Codex reasoning effort, transport, sandbox, or isolation.
`World._llm_call_kwargs` passes the OpenAI function-tool list to every generic
route and only supplies the `ae3_action` MCP server to Claude agent models. That
MCP schema also differs from the canonical action schema, but Luna does not need
either schema: the model already receives the complete decision snapshot and
produces one final action. Evaluation 07 tied its worker lifetime to an
interactive session and checkpointed the settled call separately from its
normalized decision and custody record. It ended after 189 settled calls with
only 188 complete attempt records.

The shared client supports the exact subscription route
`codex/gpt-5.6-luna`, requires explicit reasoning effort, projects Pydantic
contracts into Codex-compatible strict JSON schema, sends that schema to the
CLI with `--output-schema`, validates the result locally, and records
subscription billing. A real shared-client probe already certified a simple
structured Luna result at medium effort. It does not certify AE3's exact action
union or establish that ambient project context is absent from the direct
Codex runtime.

**Target:** From a fresh, pushed AE3 revision, one supervised representative
AE3 turn invokes exactly `codex/gpt-5.6-luna` at medium reasoning through the
ChatGPT subscription route, sees only the accepted Codex base envelope plus the
AE3 prompt and strict action schema, returns exactly one Pydantic-validated
legal action without MCP, and retains exact call/action custody. Before that
canary, provider-free checks must prove that the runtime is bound to the exact
reviewed shared-client revision, rejects unclassified Codex events, and never
refunds or erases a returned-but-invalid or dispatch-ambiguous Luna attempt.
Before any later multi-call qualification, a provider-free 16-attempt fixture
and detached worker must additionally prove that process failure cannot repeat
a dispatched provider attempt or promote ambiguous state as valid.

**Why:** Evaluation 08 cannot inherit MiniMax qualification, and another paid
batch would be indefensible until both the Luna action boundary and Evaluation
07's worker/custody failures are directly closed.

---

## Outcome, Non-Goals, and Canonical Example

### Outcome

An AE3 operator can inspect a Plan 10 evidence bundle and answer all of these
without inference:

1. Was the requested, resolved, and executed route Luna through direct Codex
   subscription at medium reasoning?
2. Did the model receive the exact AE3 messages and strict action schema from an
   empty decision workspace with no project instructions, plugins, prior
   conversation, apps, or MCP servers, and execute no Codex workspace/network
   tool?
3. Did exactly one legal action survive caller result, shared-client readback,
   normalized decision, and durable checkpoint equality?
4. Can a detached worker recover a settled response without another provider
   call, or stop with a terminal invalid receipt when exact recovery is
   unknowable?

### Canonical example

Run one provider-free Luna syscall with a fake returned shared-client result
whose route and billing are correct but whose ordered Codex event stream
contains an unclassified completed-item type. The action is rejected, while
the inspectable syscall receipt remains `provider_settled_rejected`, charges
the observed tokens/cost, consumes the reserved call, records the event types,
and permits no automatic retry. A second fixture raises after the client call
boundary is entered; it ends `dispatch_ambiguous`, retains the conservative
reservation, and likewise permits no retry. A dependency-revision mismatch
fails before reservation or dispatch.

After that example passes, separately authorize one authentic Luna Medium turn
using the prescribed production prompt and a representative state. The output
is one legal `LunaLoopDecisionV1` action plus exact route, prompt, schema, Codex
event trace, timing, token, billing, settlement, and custody evidence.

Before any later multi-call qualification, run one 16-attempt provider-free
cell with stable identity `plan10/recovery-fixture/cell-01`. Inject termination
immediately after attempt 8's shared-client settlement but before AE3 action
classification. On restart, attempt 8 is reconstructed from the retained
receipt, the cell reaches exactly 16 committed attempts, and the fake provider
dispatch count remains 16. An injection while an action is being applied
instead produces a terminal invalid cell receipt and no replacement call.

### Non-goals

- Do not edit, resume, reinterpret, or rerun Evaluation 07.
- Do not preregister or execute Evaluation 08.
- Do not qualify Luna reliability or select scarcity parameters; Plan 11 owns
  both using calibration data separate from later holdout data.
- Do not compare Luna with other models or silently fall back to OpenRouter,
  MiniMax, Terra, Sol, or another transport.
- Do not make Luna a project-wide default outside the Plan 10 configuration.
- Do not rewrite AE3, replace `llm_client`, or supersede AE2/AE3 lifecycle
  decisions.
- Do not remove or rewrite the existing MCP action bridge used by other model
  routes; it is outside Luna's MVP path.
- Do not build a generic daemon, telemetry platform, or release-hardening lane.

---

## References Reviewed

- CLAUDE.md - repository workflow, plan authority, and worktree/claim rules
- docs/plans/CLAUDE.md - plan template and current plan index
- docs/LINEAGE_AND_RESTARTS.md - observed session-lifetime and non-atomic settlement/custody failures
- docs/plans/09_behavioral_comparison_execution.md - immutable Evaluation 07 result and no-rerun rule
- docs/evaluations/07_behavioral_comparison_signoff.md - independent rejection of the behavioral claim
- src/agent_ecology3/config.py:58 - strict LLMConfig lacks Luna/Codex execution controls
- src/agent_ecology3/world/world.py:1939 - current agent-model/action-tool detection and MCP construction
- src/agent_ecology3/world/world.py:2118 - current provider keyword-argument assembly
- src/agent_ecology3/mcp/loop_action_server.py - existing Claude-oriented MCP action bridge retained outside the Luna path
- src/agent_ecology3/simulation/runner.py:33 - serialized world execution without restart state
- src/agent_ecology3/analysis/behavioral_comparison.py:1248 - Evaluation 07 post-call capture and non-atomic checkpoint boundary
- ../active/llm_client/docs/guides/codex-integration.md - direct Codex route and transport contract at revision e068430c991fd460c73d7f4faf5c92ee393b8a66
- ../active/llm_client/llm_client/core/client.py:596 - public structured-call contract at the reviewed shared-client revision
- ../active/llm_client/llm_client/sdk/agents_codex.py:47 - strict Codex Pydantic-schema projection at the reviewed revision
- ../active/llm_client/llm_client/sdk/agents_codex.py:1148 - CLI structured dispatch and local Pydantic validation at the reviewed revision
- ../active/llm_client/docs/plans/340_codex_luna_subscription_route.md:97 - retained live structured Luna evidence, including medium effort, CLI transport, isolated MCP-free home, and subscription billing
- codex-cli-v0.144.1 - `debug prompt-input` evidence observed 2026-08-12 that ambient instruction surfaces remain a blocking preflight question

---

## Existing Capability Disposition

| Concern | Owner and seam | Disposition | Adoption proof |
|---|---|---|---|
| Model routing, strict decoding, billing, retry, and trace | shared `llm_client` public `call_llm_structured`/`acall_llm_structured` boundary | **Reuse** the pinned public contract | Exact canary receipt names shared-client revision, requested/resolved/executed model, effort, transport, schema digest, retry, and billing |
| AE3 action meaning | existing loop action gate and `parse_intent_from_json` | **Extend** with one Pydantic `LunaLoopDecisionV1` union over the six permitted loop actions; unwrap into the existing parser | Provider-projected schema fixture plus one caller/readback/typed-model/parser equality trace |
| Existing MCP action bridge | `World.build_loop_action_tools` and `mcp/loop_action_server.py` | **Keep unchanged** outside the Luna MVP route | Existing MCP/runtime tests remain green; Luna captured kwargs contain neither `tools` nor `mcp_servers` |
| Simulation scheduling and action execution | `SimulationRunner` and `World` | **Extend** with opt-in recovery state; no second simulation kernel | Restart fixture resumes through the normal loop consumer path |
| Evaluation 07 runner | frozen `behavioral_comparison.py` and Evaluation 07 inputs | **Do not reuse as mutable code** | New Plan 10 module imports stable classifiers where safe but never changes Evaluation 07 identity or output |
| Strict Codex decision profile | shared Codex adapter/config surface | **Dependency probe first** | Provider-free preflight proves the exact prompt/schema, empty workspace, isolated MCP-free home, and observable intrinsic-tool policy; otherwise a separately governed `llm_client` dependency is required |

Landscape disposition is **linked**: AE3 consumes the shared client and owns its
simulation/action contract. It may not copy provider routing, auth handling, or
observability into a parallel client.

---

## Boundaries and Contracts

### 1. Luna route configuration

Add typed, fail-closed fields to `LLMConfig`; names may follow repository style,
but their semantics are fixed:

| Field | Plan 10 value | Rule |
|---|---|---|
| model | `codex/gpt-5.6-luna` | Exact route; no alias or fallback |
| reasoning effort | `medium` | Required and forwarded through the public control |
| call boundary | `acall_llm_structured` | One typed decision, not an interactive tool loop |
| transport | `cli` | No SDK-to-CLI automatic fallback |
| response model | `LunaLoopDecisionV1` | Exact versioned Pydantic union; no generic JSON object |
| retry count | `0` | No client, agent, or evaluation retry |
| sandbox | `read-only` | Empty decision workspace; no repository as working directory |
| approval | `never` | A forbidden tool fails rather than pausing for approval |
| MCP servers | none | Isolated Codex home strips ambient MCP configuration |
| intrinsic Codex tools | route substrate, zero executions | Retain the provider event trace; any shell, workspace, web, or network tool execution fails the canary |
| process boundary | CLI subprocess | Treat the CLI subprocess as the inner-call boundary; outer worker supervision remains separate |
| provider billing | `subscription_included` | API-metered execution fails the gate |

Configuration validation rejects Luna without medium effort, the exact CLI
transport, the exact response-model revision, zero retries/fallbacks, an empty
read-only workspace, an isolated MCP-free Codex home, or the approved billing
expectation before dispatch. Generic provider routes remain compatible with
their existing fields.

### 2. Prompt and structured-action boundary

The intrinsic OpenAI/Codex base instruction, permission envelope, and built-in
tool definitions are part of the selected direct route. No ambient project
source is accepted. The provider-facing inventory must exclude repository or
workspace instructions, skills, plugins, prior chat turns, apps, and ambient
MCP servers. The decision workspace is a new empty temporary directory under a
read-only sandbox. Plan 10 does not ask Codex to use a built-in tool; any
observed shell, workspace, browser, search, or network tool execution invalidates
the canary.

`LunaLoopDecisionV1` is a Pydantic envelope containing a discriminated union of
exactly the six loop actions currently permitted by the production action gate:
`write_artifact`, `read_artifact`, `transfer`, `transfer_resource`,
`submit_to_mint`, and `query_kernel`. Each variant owns its action-specific
required fields and forbids unknown fields. `query_kernel.params` uses a closed
`LunaQueryParamsV1` model containing the current kernel query keys, because the
Codex strict-schema route cannot preserve a free-form object. Semantic defaults
and query-specific requirements remain owned by the existing action gate and
parser. The shared Codex projector produces the provider schema; AE3 stores its
digest and does not maintain a second handwritten copy.

The Luna path passes neither `tools` nor `mcp_servers`. A response is usable
only when the shared client validates the exact response model, AE3 unwraps one
action, and the existing canonical parser accepts it. Hand-extracted JSON,
semantic repair, multiple actions, unknown fields, schema-version mismatch, or
any Codex tool execution fails the Plan 10 canary. AE3 alone executes the action
after validation.

### 3. Canary-safe settlement and dependency boundary

Plan 10 distinguishes the external-attempt state instead of representing every
rejected result as if no call occurred:

- A Luna configuration, schema-custody, or exact dependency-revision failure
  occurs before resource reservation and provider dispatch. The accepted
  `llm_client` execution revision is
  `286715784f1d535d6dfcd2c867ca678d666e27d5`; field-shape compatibility alone
  is insufficient.
- Once the shared-client call boundary is entered, an exception with no public
  result is `dispatch_ambiguous`. The runtime retains the call, token, and
  subscription-budget reservation, increments the syscall-attempt count,
  emits a failure receipt, and does not retry. It does not claim that the
  provider settled or charge invented actual usage.
- Once a public result returns, accounting always settles from its actual
  usage/billing even when the route profile, event policy, or action is later
  rejected. The receipt is `provider_settled_rejected`, includes the rejection
  code/message and ordered Codex event types, and remains unsuccessful for
  action execution.
- An accepted result remains `provider_settled_accepted` and follows the
  existing legal-action path.

The Plan 10 event policy is an allowlist, not only a tool denylist. Known
passive completed-item types are `reasoning` and `agent_message`. Known active
types (`command_execution`, `file_change`, `web_search`, and `mcp_tool_call`)
are forbidden, and any missing or unclassified type fails closed after truthful
settlement. Extending the passive allowlist requires a reviewed shared-client
fixture and a new exact AE3 revision; a live result does not silently teach the
policy.

This is deliberately one-call containment, not a generic recovery framework.
It is the smallest boundary that makes the authentic canary's receipt truthful.

### 4. Recoverable attempt state

Create a versioned, Pydantic-validated recovery contract. At minimum it binds:

- protocol/cell/condition/ordinal identity and configuration/source digests;
- next scheduled loop identity and logical elapsed time;
- exact messages/provider schema and their hashes;
- requested route controls and stable trace ID;
- attempt state, shared receipt/call-record identity, caller-visible result,
  normalized action/classification, and per-attempt event segment;
- recoverable World state: ledger/resources, rate windows, artifacts including
  code and timestamps, quotas, loop cognition, delegation/mint state, counters,
  logical clock, stable ID generator, and configured policy seed; and
- aggregate settled/committed counts, cost, terminal status, and checkpoint
  checksum.

Normal runs retain the current real clock/ID behavior. Recoverable evaluation
mode injects a persistent logical clock and stable ID source into every
time/identity owner used by World, artifacts, rates, delegation, mint, and the
runner. Downtime does not silently replenish a rate window or advance an
auction. There is no stateful policy RNG today; the checkpoint records the
policy seed and rejects future unregistered RNG state.

### 5. Attempt transition and recovery rules

The allowed state progression is:

```text
prepared -> dispatching -> provider_settled -> action_applying -> committed
                  |                 |                |
                  +-----------------+----------------+-> invalid_terminal
```

- `prepared` has made no provider call and may dispatch after restart.
- `dispatching` is durably written before provider invocation. On restart,
  exactly one full shared-client record for its trace permits reconstruction;
  zero, redacted, or multiple records makes the cell terminally invalid. It
  never permits a replacement call.
- `provider_settled` contains exact response/schema/typed-action custody and may
  continue through deterministic classification and application.
- `action_applying` is deliberately conservative: if no atomic committed
  checkpoint exists after a crash, the cell is terminally invalid because
  exactly-once mutation cannot be proved.
- `committed` atomically binds the post-action World snapshot, attempt record,
  event segment, scheduler cursor, and aggregate counts. Projection into JSONL
  is idempotent and may be repaired without reapplying an action.
- Checkpoint corruption, digest/config mismatch, or an unknown schema version
  fails closed and preserves the last inspectable state.

Atomic writes use a same-directory temporary file, file flush/sync, rename,
and directory sync. The prior committed checkpoint remains the recovery base;
temporary partials are evidence, not authority.

### 6. Detached supervisor

Add one operator entry point that starts, inspects, and resumes a named detached
worker. Use the available detached `tmux` process boundary for this development
profile; fail preflight when it is unavailable rather than falling back to the
interactive shell. The launch receipt records session name, PID/process group,
command, source/config digests, evidence directory, heartbeat, and exit status.

The detached worker owns provider dispatch. The launching operator process may
exit after it observes the durable launch receipt. Restart uses the stable cell
identity and recovery contract, not shell history. A provider-free lifecycle
test must terminate the launcher and worker independently and demonstrate that
the supervisor preserves or restarts the cell without duplicate dispatch.

---

## Plan

### Risk-Ordered Implementation Horizon

#### Slice A - exact Luna/action boundary (`exploration_required`)

1. Extend strict AE3 config and its provider-dispatch seam for the exact Plan 10
   route.
2. Define `LunaLoopDecisionV1` from the production loop-action set, project it
   through the shared Codex schema compiler, and feed every variant through the
   existing canonical action parser. Provider-free schema compilation must keep
   exactly six top-level action branches and no open object node.
3. Route Luna through `acall_llm_structured` without `tools` or `mcp_servers`;
   retain existing generic/MCP behavior for other models.
4. Generate the exact isolated Codex command, home configuration,
   provider-facing prompt/schema inventory, and event-capture contract without
   a provider call.
5. Stop if the shared client cannot exclude ambient project instructions and
   MCP servers, pass the exact schema to CLI, or expose enough CLI events to
   detect built-in tool execution. Route the smallest missing capability to
   `llm_client`; do not implement an AE3-private provider/auth client and do not
   weaken the gate.

**Readout:** one machine-readable inventory names every message source, schema
digest, working directory, Codex-home source, MCP server, relevant intrinsic
tool surface, and executed command. Pass requires the accepted Codex base route,
the exact AE3 messages/schema, an empty decision workspace, no MCP servers, and
an event contract that makes any intrinsic tool use visible.

**Promotion:** passing inventory freezes `LunaStructuredActionV1` for the
remaining Plan 10 slices. Failure returns `blocked` with the observed surface
and exact shared dependency; OpenRouter remains a user decision, not an
automatic branch.

#### Slice B - truthful one-call settlement (`fully_specifiable_now`)

1. Bind production Luna preflight to the exact accepted `llm_client` revision,
   while retaining the existing public-field shape check as a separate
   diagnostic.
2. Classify post-boundary exceptions as `dispatch_ambiguous`; retain reserved
   resources and record one unsuccessful attempt without retry.
3. Settle every returned result from actual usage/billing before rejecting an
   invalid route profile, Codex event stream, or action.
4. Replace the intrinsic-event denylist with the reviewed passive allowlist and
   fail closed on missing or unknown completed-item types.
5. Cover the synchronous and asynchronous production consumers with focused
   provider-free fixtures, including the canonical example above.

**Acceptance:** a returned-but-rejected result and an ambiguous dispatch both
remain visible unsuccessful attempts and cannot replenish resources or trigger
a replacement call; an exact dependency mismatch fails before reservation;
known passive events pass and active/unknown events fail closed.

#### Slice C - one authentic Luna canary (`human_decision_required`)

This slice begins only after Slice B passes and the user separately authorizes
the external call. It runs exactly once through the frozen production
prompt/action/settlement path. Any route, auth, quota, timeout, ambient-surface,
schema, intrinsic-tool execution, custody, action, accounting, or billing
failure retains a `blocked` evidence bundle and ends the canary without retry
or route switch.

The canary is allowed before the detached worker because it is one reversible,
serial call with no retry and a retained terminal receipt. It does not
establish a reliability rate, behavioral effect, valid scarcity treatment, or
permission for a paid batch.

#### Slice D - recoverable cell and custody (`conditional`)

**Selecting condition:** the canary passes and the operator proposes any
multi-call Luna qualification or evaluation.

1. Introduce the typed attempt/checkpoint contract and append-safe logger mode.
2. Add logical clock/stable identity injection and World export/restore for the
   state enumerated above.
3. Drive normal AE3 loop execution through the transition contract in an
   opt-in recoverable mode.
4. Reconstruct `dispatching`/`provider_settled` attempts only from exact public
   shared-client readback; never call the provider from recovery.
5. Buffer and atomically commit the attempt record, World snapshot, scheduler
   cursor, event segment, and aggregate counters.
6. Exercise termination at every transition using provider-free fixtures,
   including the canonical 8-of-16 example and checkpoint corruption.

**Acceptance:** every injected failure either reaches the same 16 committed
attempts with 16 dispatches or produces a named terminal invalid receipt with
no additional dispatch. No fixture may silently restart from an empty World.

#### Slice E - detached worker (`conditional`)

**Selecting condition:** Slice D passes and a multi-call Luna run is the next
authorized action.

1. Add `start`, `status`, and `resume` behavior around the recoverable cell.
2. Retain launch/heartbeat/exit receipts outside automatic prompt discovery.
3. Prove with the provider-free fixture that launcher exit does not terminate
   the worker and worker termination invokes the recovery contract.

**Acceptance:** a new operator process can inspect the stable run identity,
last committed attempt, current/terminal state, and exact resume action without
access to the original chat or PTY. Plan 11 remains blocked until the canary
passes and cannot execute a multi-call run until Slices D-E pass.

---

## External Call Budget

```yaml
external_call_budget:
  calls:
    total: 1
    per_purpose:
      luna_medium_structured_action_canary: 1
  serial_depth_and_parallelism: "one call; serial depth 1; parallel width 1"
  context_bound: >-
    Render and record exact message/schema bytes and the current Codex route
    limit before dispatch; stop if the payload exceeds the effective limit.
    The canary records observed input/output tokens rather than assuming them.
  cost_and_latency: >-
    Require subscription_included billing and observed provider USD 0.00.
    Subscription quota consumption and latency are measured by the canary.
    Preserve AE3's current 90-second call boundary; timeout is terminal.
  completion_evidence: >-
    Exact requested/resolved/executed model and medium effort, CLI transport,
    exact prompt/schema digest, no MCP servers, zero observed Codex tool
    executions, one Pydantic-validated legal action, full
    caller/readback/typed-action/decision custody, trace, usage, timing, and
    billing receipt.
  retry_repair_fallback: >-
    zero retries, zero semantic repair calls, zero fallback models, and no
    invisible transport or provider switch; a failed settled call ends the gate.
  checkpoint_and_resume: >-
    stable identity plan10/luna-medium/canary/v1; evidence under
    docs/evaluations/evidence/plan10_luna_recovery_gate/. Recovery may consume
    an exact settled readback but may never dispatch a replacement call.
```

Planning and implementation do not authorize this call. The live flag and exact
one-call acknowledgement must remain unavailable until separate authorization.

---

## Files Affected

- src/agent_ecology3/config.py (modify)
- src/agent_ecology3/world/world.py (modify)
- src/agent_ecology3/world/logger.py (modify)
- src/agent_ecology3/world/artifacts.py (modify)
- src/agent_ecology3/world/rates.py (modify)
- src/agent_ecology3/world/delegation.py (modify)
- src/agent_ecology3/world/mint.py (modify)
- src/agent_ecology3/simulation/runner.py (modify)
- src/agent_ecology3/analysis/luna_recovery_gate.py (create)
- config/config.luna_recovery_gate.yaml (create)
- scripts/run_recoverable_evaluation.py (create)
- tests/test_runtime_smoke.py (modify)
- tests/test_luna_recovery_gate.py (create)
- docs/evaluations/evidence/plan10_luna_recovery_gate/ (create)
- docs/LINEAGE_AND_RESTARTS.md (modify)
- README.md (modify)
- docs/plans/10_luna_medium_recovery_gate.md (modify)
- docs/plans/CLAUDE.md (modify)

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|---|---|---|
| tests/test_luna_recovery_gate.py | test_luna_route_requires_exact_medium_cli_profile | Omissions, aliases, retries, fallback, API billing, and unsupported effort fail closed |
| tests/test_luna_recovery_gate.py | test_luna_action_schema_projects_six_permitted_variants | One Pydantic union covers the production loop-action set with six branches and no open object node |
| tests/test_luna_recovery_gate.py | test_luna_structured_kwargs_are_explicit_and_mcp_free | The production consumer adopts the exact shared structured route without tools or MCP servers |
| tests/test_luna_recovery_gate.py | test_prompt_schema_profile_is_ambient_free_and_observes_tool_event_custody | The profile has only accepted context, an empty workspace, no MCP, and ordered public intrinsic-event custody |
| tests/test_luna_recovery_gate.py | test_luna_dependency_revision_mismatch_fails_before_reservation | Field-compatible but unreviewed shared-client source cannot enter the call boundary |
| tests/test_luna_recovery_gate.py | test_luna_returned_rejection_settles_accounting_and_receipt | Returned invalid results consume the call and settle actual usage instead of being refunded |
| tests/test_luna_recovery_gate.py | test_luna_dispatch_ambiguity_retains_reservation_without_retry | An exception after entering the client boundary is a visible conservative attempt, not a free retry |
| tests/test_luna_recovery_gate.py | test_luna_unknown_codex_event_fails_closed_after_settlement | Missing or unclassified Codex item types cannot be promoted as passive |
| tests/test_luna_recovery_gate.py | test_attempt_state_machine_rejects_invalid_transitions | Unknown versions and illegal transitions fail closed |
| tests/test_luna_recovery_gate.py | test_post_settlement_restart_does_not_duplicate_dispatch | The canonical 8-of-16 restart finishes with exactly 16 fake dispatches |
| tests/test_luna_recovery_gate.py | test_action_application_crash_is_terminal | Ambiguous mutation cannot trigger a replacement dispatch |
| tests/test_luna_recovery_gate.py | test_checkpoint_corruption_and_identity_mismatch_fail_closed | Truncation, digest mismatch, stale partials, and wrong identity cannot be promoted |
| tests/test_luna_recovery_gate.py | test_world_snapshot_round_trip_preserves_visible_and_accounting_state | Restored World state matches model-visible and accounting state |
| tests/test_luna_recovery_gate.py | test_detached_worker_survives_launcher_and_recovers_worker_exit | Worker lifetime is independent of the interactive launcher and recovery is inspectable |
| tests/test_luna_recovery_gate.py | test_live_canary_requires_exact_one_call_acknowledgement | The live path is inaccessible without the separate exact one-call gate |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|---|---|
| tests/test_runtime_smoke.py | Existing route, action, and simulation behavior remains compatible |

Run the smallest focused tests during implementation. Before the canary, run
the complete provider-free Plan 10 preflight and canonical recovery example.
The full repository suite and documentation coupling check are terminal
integration checks for the coherent implementation revision, not per-edit
loops.

---

## Acceptance Criteria

- [x] Exact Luna Medium configuration is typed, fail-closed, and used by the
      production AE3 loop consumer.
- [x] Provider-facing preflight proves the exact prompt/schema, empty workspace,
      isolated MCP-free home, and intrinsic-tool event visibility; otherwise
      the plan stops at a named shared dependency.
- [x] `LunaLoopDecisionV1` covers every permitted production loop action and
      retains one normalized action through shared-client readback and the
      existing canonical parser.
- [x] Luna passes neither tools nor MCP servers, while the existing MCP path for
      other routes remains unchanged.
- [x] Production preflight binds Luna to the exact reviewed `llm_client`
      revision before resource reservation or provider dispatch.
- [x] Returned-but-rejected and dispatch-ambiguous Luna attempts retain
      truthful resources, counts, settlement state, and failure receipts with
      no automatic retry.
- [x] Only reviewed passive Codex event types are accepted; active, missing,
      and unknown types fail closed after truthful settlement.
- [ ] The canonical 16-attempt recovery fixture completes with exactly 16 fake
      dispatches after a post-settlement restart.
- [ ] Every ambiguous in-flight/action/corrupt-checkpoint case is terminally
      invalid and causes no replacement dispatch.
- [ ] Restored World, scheduler, logical time/ID, accounting, artifacts, and
      model-visible state match the last committed checkpoint.
- [ ] A detached worker survives launcher exit and exposes truthful status and
      resume evidence to a new process.
- [x] The live entry point refuses dispatch without exact one-call human
      acknowledgement.
- [x] After separate authorization, one and only one authentic canary either
      passes every route/action/custody gate or retains a blocked bundle naming
      the failed boundary.
- [ ] No Evaluation 07 input/evidence changes, no Evaluation 08 claim is made,
      and Plan 11 remains blocked unless the canary passes.

---

## Failure, Cleanup, and Reset Boundary

- A pre-dispatch failure makes zero external calls and leaves an inspectable
  provider-free preflight result.
- A dispatch-ambiguous Luna failure retains its conservative reservation and
  attempt receipt because the runtime cannot prove the provider was untouched.
- A returned-but-rejected Luna result settles actual usage and remains
  inspectable; action failure cannot retroactively turn the call into a refund.
- A settled canary failure is final for the executed Plan 10 revision. Preserve
  it; do not tune the prompt, repair semantically, retry, or switch route under
  the same gate.
- A recovery ambiguity marks only the affected fixture/cell invalid; it never
  deletes the prior checkpoint or shared receipt.
- Runtime auth links and isolated Codex configuration stay in a temporary
  non-evidence directory and are removed after the process; evidence contains
  identities/digests, never credentials.
- Detached fixture sessions are stopped after their terminal receipt. Evidence
  remains recoverable Git content only after secret scanning and manifesting.
- Shared progress tripwires apply: course-check after roughly 45 minutes without
  an authentic capability, two consecutive non-outcome increments, or three
  failures at the same boundary. The outcome and gates do not silently shrink.

The next action is the human-decision boundary for Slice C: separately
authorize one authentic Luna Medium call through the frozen production path.
Until that exact authorization is given, no provider call is permitted. A
passing canary selects the conditional Slices D-E before any multi-call run; a
failed canary remains a terminal blocked receipt with no retry or route switch.

The listed files are the expected AE3 surfaces and may be narrowed during
implementation. Plan 10 may not add a parallel LLM client or alter Evaluation
07. If Slice A finds a missing shared capability, create a separately governed
`llm_client` plan and claim before changing that repository; its public
contract, fixtures, and pinned revision become a Plan 10 dependency.
