# Plan #5: Experiment Instrument Repair and Provider Qualification

**Status:** Complete
**Type:** implementation
**Priority:** High
**Blocked By:** None
**Blocks:** A fresh prescribed-versus-minimal behavioral evaluation

---

## Gap

**Current:** Evaluation 04 is correctly classified as inconclusive. Its
asynchronous simulation monitor is blocked by synchronous provider calls, its
behavioral-validity denominator mixes provider/tool failures with agent action
validity, and its shared-client records predate durable tool-call payload
custody.

**Target:** Give autonomous loop artifacts an async execution boundary that
keeps the simulation monitor responsive, prove that an in-flight provider call
is drained before the runner returns, consume the shared client's durable
tool-call payload, and run a separately preregistered reliability qualification
for the exact model/prompt/tool contract. A behavioral comparison remains out
of scope until that qualification passes.

**Why:** Another ablation using the old instrument would mostly measure
transport truncation and scheduler blocking. Repair and qualify the measuring
instrument before spending on behavioral replicates.

---

## References Reviewed

- `docs/evaluations/04_prescription_ablation.md` - frozen inconclusive result,
  observed failure modes, and explicit recommendation.
- `src/agent_ecology3/simulation/runner.py:99-221` - synchronous loop invocation
  currently blocks the event loop and cancellation can orphan thread work.
- `src/agent_ecology3/world/executor.py:78-260` - executable-artifact boundary
  and synchronous `_syscall_llm` injection.
- `src/agent_ecology3/world/action_executor.py:306-510` - invocation accounting,
  loop-decision attribution, and current synchronous executor call.
- `src/agent_ecology3/world/world.py:807-1630,1887-2145` - generated loop prompt,
  tool schema, syscall accounting, and provider dispatch.
- `llm_client` Plan #350 / merge `e068430` - authoritative full-content
  `response_tool_calls` persistence and exact-call readback.
- `config/prompts/loop_prompt_variant.txt` and
  `config/prompts/loop_prompt_minimal.txt` - frozen cognition prompts.

---

## Files Affected

- `src/agent_ecology3/simulation/runner.py`
- `src/agent_ecology3/world/executor.py`
- `src/agent_ecology3/world/action_executor.py`
- `src/agent_ecology3/world/world.py`
- `src/agent_ecology3/analysis/provider_qualification.py` (create)
- `tests/test_runtime_smoke.py`
- `tests/test_provider_qualification.py` (create)
- `config/config.provider_qualification.yaml` (create)
- `config/evaluations/05_fixed_state.json` (create)
- `docs/evaluations/05_provider_tool_qualification.md` (create, append only
  after the frozen run)
- `docs/evaluations/evidence/05_provider_tool_qualification/` (generated only
  after the frozen run)
- `docs/plans/05_experiment_instrument_repair.md`
- `docs/plans/CLAUDE.md`

---

## Plan

1. Add failing tests proving that a slow provider await does not stop an
   independent heartbeat or duration monitor, loop executions remain
   serialized, and `run()` does not return while an invocation can still
   mutate the world.
2. Add an async executable-artifact route for autonomous loop `run` methods.
   Keep world mutation on the simulation event loop; use `llm_client.acall_llm`
   only at the provider await. Preserve the existing synchronous route for
   non-runner callers.
3. Refactor syscall reservation, settlement, logging, and failure cleanup so
   sync and async provider dispatch share one accounting contract.
4. Add a deterministic qualification classifier and runner for the frozen
   Evaluation 05 cases. Require exact shared-client tool-call custody rather
   than trusting an AE3-local normalized copy.
5. Run the focused and full local gates. Only then run the preregistered paid
   qualification once, without retries or threshold changes.
6. Preserve exact inputs, attempt records, receipts/call records, result
   classification, and a SHA-256 manifest. Do not start a behavioral evaluation
   unless Evaluation 05 passes and a new evaluation is preregistered.

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|---|---|---|
| `tests/test_runtime_smoke.py` | `test_runner_monitor_remains_responsive_during_slow_async_syscall` | A slow provider await does not block an independent heartbeat or the runner's duration checks. |
| `tests/test_runtime_smoke.py` | `test_runner_drains_inflight_loop_before_returning` | Stop requests do not orphan work that mutates the world after `run()` returns. |
| `tests/test_runtime_smoke.py` | `test_runner_serializes_loop_world_mutations` | Multiple autonomous loops do not concurrently mutate shared world state. |
| `tests/test_runtime_smoke.py` | `test_legacy_sync_artifact_can_still_invoke_nested_artifact` | The async runner route does not break existing synchronous nested artifacts. |
| `tests/test_runtime_smoke.py` | `test_async_syscall_uses_shared_accounting_and_native_async_client` | The async boundary dispatches through `acall_llm` with the same trace and budget contract. |
| `tests/test_provider_qualification.py` | `test_valid_tool_call_and_exact_custody_pass` | A legal `ae3_action` plus identical durable tool-call readback is usable. |
| `tests/test_provider_qualification.py` | `test_malformed_or_missing_tool_call_fails` | Missing, malformed, or illegal actions fail qualification visibly. |
| `tests/test_provider_qualification.py` | `test_truncation_and_custody_mismatch_fail` | Transport truncation and non-identical durable payloads are separate hard failures. |
| `tests/test_provider_qualification.py` | `test_metadata_only_call_record_fails_custody` | A redacted call record cannot satisfy exact-custody qualification. |
| `tests/test_provider_qualification.py` | `test_nonidentical_retained_response_fails_custody` | Public readback must match caller-visible response content even when persistence metadata is absent. |
| `tests/test_provider_qualification.py` | `test_frozen_case_order_is_balanced_and_alternating` | The 32-call dispatch order stays balanced and serially alternating. |
| `tests/test_provider_qualification.py` | `test_frozen_summary_requires_threshold_and_zero_hard_failures` | The frozen 15/16 threshold passes only without timeout or truncation failures. |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|---|---|
| `tests/test_runtime_smoke.py` | Existing loop behavior, syscall accounting, and action attribution remain compatible. |
| `tests/test_scarcity_matrix.py` | Simulation stop and paid-run validity behavior remain compatible. |
| `tests/test_config_and_actions.py` | Configuration and action parsing remain compatible. |

---

## Acceptance Criteria

- [x] The runner's monitor remains responsive during a slow provider call.
- [x] Autonomous loop world mutations are serialized and fully drained before
      `SimulationRunner.run()` returns.
- [x] Sync and async syscalls share reservation, settlement, trace, cost, and
      error-cleanup behavior.
- [x] Exact public tool-call payloads are reopened from shared-client storage
      and compared with the AE3 result for every successful qualification call.
- [x] Evaluation 05 is executed exactly once under its frozen gate and evidence
      contract, or is stopped before dispatch if local controls fail.
- [x] Focused tests, full tests, changed-file type checking, and diff hygiene
      pass. Repository-wide mypy still reports 27 pre-existing errors in eight
      unrelated modules.
- [x] No Evaluation 04 result or threshold is modified, and no fresh behavioral
      evaluation begins without a new preregistration.

---

## Failure Handling

The production bootstrap route awaits the native async provider client. Legacy
synchronous loop artifacts are offloaded as one serialized invocation and are
also drained before return. On runner stop, new iterations cease but an
in-flight invocation is awaited to terminal completion; provider timeout is the
outer bound. Evaluation 05 stops immediately on trace/custody corruption,
budget exhaustion, or an unexpected configuration hash. A failed qualification
is a result, not permission to tune and rerun.

---

## Completion Evidence

- Runtime/classifier gate: 58 required tests passed after the post-run custody
  regression fix.
- Full repository suite: 71 tests passed.
- Changed source files: mypy passed with no issues; document coupling and
  `git diff --check` passed.
- Evaluation 05 ran once from clean pushed revision `d9ad310`; 32/32 calls and
  the evidence manifest completed for USD 0.0359061.
- Frozen verdict: `not_qualified` because the classifier expected an
  unexposed readback metadata key. Exact payload audit was 16/16 prescribed
  and 15/16 minimal, but was not promoted into a qualification decision and no
  rerun or behavioral evaluation was started.
