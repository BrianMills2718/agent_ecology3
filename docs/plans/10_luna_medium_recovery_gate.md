# Plan #10: Luna Medium Compatibility and Recovery Gate

**Status:** Planned
**Type:** implementation
**Priority:** High
**Blocked By:** None; live canary dispatch remains separately authorized
**Blocks:** Luna-specific qualification and scarcity calibration (Plan #11)

---

## Adopted Direction

The user selected Luna Medium and accepted the staged Plan 10-12 direction on
2026-08-12. This plan is the implementation-ready translation of the first
stage. Reversible technical details use the recommended path below. A change of
model, route, account/billing mode, call count, or success boundary returns to
the user rather than proceeding implicitly.

**Planning route:** durable solo. Work is sequential, but the experimental
instrument and recovery contract are durable consumers. No work-unit graph or
parallel lane is justified yet.

**Delivery profile:** prototype instrument with runtime-state, LLM, exploratory,
and repository-governance overlays. This plan proves a route and a recoverable
cell; it does not promote AE3 to an operational service or execute a behavioral
evaluation.

---

## Gap

**Current:** AE3's LLM configuration cannot express Codex reasoning effort,
execution mode, transport, sandbox, or isolation. `World._llm_call_kwargs`
passes the OpenAI function-tool list to every route but only supplies the
`ae3_action` MCP server to Claude agent models. The existing MCP server also
omits provider-contract fields such as `read_price`, `invoke_price`, and
`access_contract_id`. Evaluation 07 tied its worker lifetime to an interactive
session and checkpointed the settled call separately from its normalized
decision and custody record. It ended after 189 settled calls with only 188
complete attempt records.

The shared client supports the exact subscription route
`codex/gpt-5.6-luna`, requires explicit reasoning effort, can carry Codex MCP
calls into `LLMCallResult.tool_calls`, and records subscription billing. It
does not establish that the direct Codex agent can expose an action-only tool
surface: Codex has intrinsic workspace-agent instructions and built-in tools,
and the current AE3 adapter does not constrain or inspect them.

**Target:** From a fresh, pushed AE3 revision, one supervised representative
AE3 turn invokes exactly `codex/gpt-5.6-luna` at medium reasoning through the
ChatGPT subscription route, sees only the accepted Codex base envelope plus the
AE3 prompt, submits exactly one legal `ae3_action`, and retains exact
call/action custody. Before that canary, a provider-free 16-attempt fixture must
prove that a worker or process failure cannot repeat a dispatched provider
attempt and cannot promote ambiguous state as valid.

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
2. Did the model receive the exact AE3 messages and canonical action contract
   without project instructions, plugins, prior conversation, web/network
   access, or non-AE3 callable tools?
3. Did exactly one legal action survive caller result, shared-client readback,
   normalized decision, and durable checkpoint equality?
4. Can a detached worker recover a settled response without another provider
   call, or stop with a terminal invalid receipt when exact recovery is
   unknowable?

### Canonical example

Run one 16-attempt provider-free cell with stable identity
`plan10/recovery-fixture/cell-01`. Inject termination immediately after attempt
8's shared-client settlement but before AE3 action classification. On restart,
attempt 8 is reconstructed from the retained receipt, the cell reaches exactly
16 committed attempts, and the fake provider dispatch count remains 16. A
second injection while an action is being applied must instead produce a
terminal invalid cell receipt and no replacement call.

After that example passes, separately authorize one authentic Luna Medium
turn using the prescribed production prompt and a representative state. The
inspectable output is one legal `ae3_action` plus exact route, prompt, tool,
trace, timing, token, billing, and custody evidence.

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
- src/agent_ecology3/mcp/loop_action_server.py - AE3-owned MCP action bridge and provider-schema mismatch
- src/agent_ecology3/simulation/runner.py:33 - serialized world execution without restart state
- src/agent_ecology3/analysis/behavioral_comparison.py:1248 - Evaluation 07 post-call capture and non-atomic checkpoint boundary
- ../active/llm_client/docs/guides/codex-integration.md - direct Codex route and transport contract at revision e068430c991fd460c73d7f4faf5c92ee393b8a66
- ../active/llm_client/llm_client/core/client.py:729 - public call contract at the reviewed shared-client revision
- ../active/llm_client/llm_client/sdk/agents_codex.py:483 - CLI MCP call extraction and subscription observability at the reviewed revision
- codex-cli-v0.144.1 - `debug prompt-input` evidence observed 2026-08-12 that ambient instruction surfaces remain a blocking preflight question

---

## Existing Capability Disposition

| Concern | Owner and seam | Disposition | Adoption proof |
|---|---|---|---|
| Model routing, billing, retry, trace, and MCP extraction | shared `llm_client` public `call_llm`/`acall_llm` boundary | **Reuse** the pinned public contract | Exact canary receipt names shared-client revision, requested/resolved/executed model, effort, transport, retry, billing, and tool calls |
| AE3 action meaning | `World.build_loop_action_tools`, `parse_intent_from_json`, and action gate | **Extend** the existing MCP bridge to match this canonical seam | Provider schema and MCP schema parity test plus one production parser/action trace |
| Simulation scheduling and action execution | `SimulationRunner` and `World` | **Extend** with opt-in recovery state; no second simulation kernel | Restart fixture resumes through the normal loop consumer path |
| Evaluation 07 runner | frozen `behavioral_comparison.py` and Evaluation 07 inputs | **Do not reuse as mutable code** | New Plan 10 module imports stable classifiers where safe but never changes Evaluation 07 identity or output |
| Strict Codex prompt/tool profile | shared Codex adapter/config surface | **Dependency probe first** | Provider-facing preflight proves the accepted prompt/tool inventory; otherwise a separately governed `llm_client` dependency is required |

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
| execution mode | `workspace_agent` | Explicit agent capability contract |
| transport | `cli` | No SDK-to-CLI automatic fallback |
| retry count | `0` | No client, agent, or evaluation retry |
| sandbox | `read-only` | Empty decision workspace; no repository as working directory |
| approval | `never` | A forbidden tool fails rather than pausing for approval |
| network/web | disabled | The absence is verified in the effective route profile |
| process boundary | CLI subprocess | Treat the CLI subprocess as the inner-call boundary; outer worker supervision remains separate |
| provider billing | `subscription_included` | API-metered execution fails the gate |

Configuration validation rejects Luna without medium effort, the exact CLI
transport, the action-only profile, zero retries/fallbacks, or the approved
billing expectation before dispatch. Generic provider routes remain compatible
with their existing fields.

### 2. Prompt and tool boundary

The intrinsic OpenAI/Codex base instruction and permission envelope are part of
the selected direct route. No other ambient source is accepted. In particular,
the provider-facing inventory must exclude repository/workspace instructions,
skills, plugins, prior chat turns, apps, browser/search, shell/workspace tools,
and ambient MCP servers.

The sole callable tool is AE3's `ae3_action`. Its MCP schema and the canonical
provider function schema must expose the same action fields and requiredness.
Tool names normalized by Codex may be qualified with their MCP server; AE3's
existing exact-or-suffix parser remains the compatibility rule. A response is
usable only when exactly one successful matching tool call parses to a legal
AE3 intent. JSON text fallback, a non-AE3 tool call, multiple action calls, or
an MCP error fails the Plan 10 canary.

### 3. Recoverable attempt state

Create a versioned, Pydantic-validated recovery contract. At minimum it binds:

- protocol/cell/condition/ordinal identity and configuration/source digests;
- next scheduled loop identity and logical elapsed time;
- exact messages/tools and their hashes;
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

### 4. Attempt transition and recovery rules

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
- `provider_settled` contains exact response/tool custody and may continue
  through deterministic classification and application.
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

### 5. Detached supervisor

Add one operator entry point that starts, inspects, and resumes a named detached
worker. Use the available detached `tmux` process boundary for this development
profile; fail preflight when it is unavailable rather than falling back to the
interactive shell. The launch receipt records session name, PID/process group,
command, source/config digests, evidence directory, heartbeat, and exit status.

The detached worker owns provider dispatch. The launching chat/tool process may
exit after it observes the durable launch receipt. Restart uses the stable cell
identity and recovery contract, not shell history. A provider-free lifecycle
test must terminate the launcher and worker independently and demonstrate that
the supervisor preserves or restarts the cell without duplicate dispatch.

---

## Plan

### Risk-Ordered Implementation Horizon

#### Slice A - exact Luna/action boundary (`exploration_required`)

1. Extend strict AE3 config and `_llm_call_kwargs` for the exact Plan 10 route.
2. Reconcile the MCP action schema with the canonical provider schema and add a
   structural parity test.
3. Generate the exact isolated Codex profile and provider-facing prompt/tool
   inventory without a provider call.
4. Stop if the existing shared client cannot exclude ambient instructions and
   non-AE3 tools while retaining subscription auth and the required MCP server.
   Route the smallest missing capability to `llm_client`; do not implement an
   AE3-private provider/auth client and do not weaken the gate.

**Readout:** one machine-readable inventory names every message source and
callable tool. Pass requires only the accepted Codex base/permission envelope,
the exact AE3 messages, and `ae3_action`.

**Promotion:** passing inventory freezes `LunaActionRouteV1` for the remaining
Plan 10 slices. Failure returns `blocked` with the observed surface and exact
shared dependency; OpenRouter remains a user decision, not an automatic branch.

#### Slice B - recoverable cell and custody (`fully_specifiable_now`)

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

#### Slice C - detached worker (`fully_specifiable_now`)

1. Add `start`, `status`, and `resume` behavior around the recoverable cell.
2. Retain launch/heartbeat/exit receipts outside automatic prompt discovery.
3. Prove with the provider-free fixture that launcher exit does not terminate
   the worker and worker termination invokes the recovery contract.

**Acceptance:** a new operator process can inspect the stable run identity,
last committed attempt, current/terminal state, and exact resume action without
access to the original chat or PTY.

#### Slice D - one authentic Luna canary (`human_decision_required`)

This slice begins only after A-C pass and the user separately authorizes the
external call. It runs once through the detached worker with the exact frozen
prompt/action/recovery path. Any route, auth, quota, timeout, tool-surface,
custody, action, or billing failure retains a `blocked` evidence bundle and
ends Plan 10 without retry or route switch.

Plan 11 is selected only if the canary passes. The canary does not establish a
reliability rate, behavioral effect, or valid scarcity treatment.

---

## External Call Budget

```yaml
external_call_budget:
  calls:
    total: 1
    per_purpose:
      luna_medium_ae3_action_canary: 1
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
    action-only prompt/tool inventory, one successful legal ae3_action, full
    caller/readback/decision custody, trace, usage, timing, and billing receipt.
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
- src/agent_ecology3/mcp/loop_action_server.py (modify)
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
| tests/test_luna_recovery_gate.py | test_action_mcp_schema_matches_world_contract | The MCP surface exposes every canonical AE3 action field and requiredness rule |
| tests/test_luna_recovery_gate.py | test_luna_call_kwargs_are_explicit_and_scoped | The production consumer adopts the exact shared-client route and scoped MCP server |
| tests/test_luna_recovery_gate.py | test_prompt_tool_inventory_is_ae3_only | Provider-facing context contains only the accepted base envelope, AE3 messages, and action tool |
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

- [ ] Exact Luna Medium configuration is typed, fail-closed, and used by the
      production AE3 loop consumer.
- [ ] Provider-facing preflight proves the accepted prompt and action-only tool
      surface; otherwise the plan stops at a named shared dependency.
- [ ] The MCP bridge matches the canonical action contract and retains one
      normalized `ae3_action` through shared-client readback.
- [ ] The canonical 16-attempt recovery fixture completes with exactly 16 fake
      dispatches after a post-settlement restart.
- [ ] Every ambiguous in-flight/action/corrupt-checkpoint case is terminally
      invalid and causes no replacement dispatch.
- [ ] Restored World, scheduler, logical time/ID, accounting, artifacts, and
      model-visible state match the last committed checkpoint.
- [ ] A detached worker survives launcher exit and exposes truthful status and
      resume evidence to a new process.
- [ ] The live entry point refuses dispatch without exact one-call human
      acknowledgement.
- [ ] After separate authorization, one and only one authentic canary either
      passes every route/action/custody gate or retains a blocked bundle naming
      the failed boundary.
- [ ] No Evaluation 07 input/evidence changes, no Evaluation 08 claim is made,
      and Plan 11 remains blocked unless the canary passes.

---

## Failure, Cleanup, and Reset Boundary

- A pre-dispatch failure makes zero external calls and leaves an inspectable
  provider-free preflight result.
- A settled canary failure is final for Plan 10 revision 1. Preserve it; do not
  tune the prompt, repair semantically, retry, or switch route under the same
  gate.
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

The next action after this plan is accepted in the repository is Slice A's
provider-free action/profile preflight. No provider call is part of plan
authoring or ordinary implementation.

The listed files are the expected AE3 surfaces and may be narrowed during
implementation. Plan 10 may not add a parallel LLM client or alter Evaluation
07. If Slice A finds a missing shared capability, create a separately governed
`llm_client` plan and claim before changing that repository; its public
contract, fixtures, and pinned revision become a Plan 10 dependency.
