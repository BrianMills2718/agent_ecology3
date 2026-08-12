# Plan #8: Behavioral Comparison Runner

**Status:** Complete
**Type:** implementation
**Priority:** High
**Blocked By:** Plan #7 complete
**Blocks:** Separately authorized Evaluation 07 execution

---

## Gap

**Current:** Evaluation 07 freezes its paired schedule, attempt boundary,
controls, validity rules, readout, evidence contract, and spend ceiling, but no
executable one-shot runner or saved-artifact reproducer exists.

**Target:** Add one orchestration owner that can run every zero-provider
preflight, stop simulations after exactly 16 settled provider attempts, retain
the complete caller/public-readback/action chain, apply pair/reserve rules, and
reproduce the frozen readout without a provider or observability database.

**Why:** The preregistration is useful only if execution cannot silently fall
back to the successful-call stopping rule, mutate thresholds, lose behavioral
action custody, or reinterpret an invalid pair after seeing results.

---

## Frozen Boundaries Reviewed

- `docs/evaluations/07_behavioral_comparison.md`
- `config/config.behavioral_comparison_07.yaml`
- `config/evaluations/07_behavioral_cases.json`
- `src/agent_ecology3/analysis/provider_qualification.py`
- `src/agent_ecology3/analysis/emergence_report.py`
- `src/agent_ecology3/simulation/runner.py`
- `src/agent_ecology3/world/world.py`
- Eval06 evidence manifest and independent signoff

The Eval07 document, config, case schedule, prompts, model, treatment package,
thresholds, deadline, and budget are immutable in this plan.

---

## Files Affected

- `src/agent_ecology3/analysis/behavioral_comparison.py` (create)
- `src/agent_ecology3/simulation/runner.py` (attempt-stop infrastructure only;
  default behavior unchanged)
- `tests/test_behavioral_comparison.py` (create)
- `tests/test_runtime_smoke.py` (focused exact-stop regression if needed)
- `README.md` and `docs/CHATGPT_FULL_CONTEXT.md` (implementation/not-run status)
- `docs/LINEAGE_AND_RESTARTS.md` (next legitimate step)
- `docs/plans/08_behavioral_comparison_runner.md`
- `docs/plans/CLAUDE.md`

---

## Plan

1. Write failing tests for frozen hash/schedule validation, exact attempt
   stopping, metric/readback/corruption controls, pair validity, exact readout,
   and saved-artifact reproduction.
2. Add an optional settled-attempt target to `SimulationRunner`; check the
   target while holding its serial world lock and recheck the stop flag before
   any waiting loop invokes. Preserve default runner behavior.
3. Implement Eval07 preflight by reusing the proven Eval06 public-readback
   boundary and exercising positive, negative, corruption, LLM-off, hash,
   deadline, leakage, schedule, and spend controls without a provider.
4. Implement one-shot pair orchestration, caller/public-readback capture,
   normalized-action/event linkage, scarcity receipts, run/pair validity,
   ordered reserve use, hard cost/call ceilings, and partial-evidence failure
   preservation.
5. Implement deterministic readout and evidence reproduction from the manifest
   plus saved files only.
6. Verify and publish the clean runner. Do not pass `--run-live` or dispatch a
   provider call.

---

## Required Tests

### New Tests

| Test File | Test Function | What It Verifies |
|---|---|---|
| `tests/test_behavioral_comparison.py` | `test_frozen_inputs_schedule_and_budget_pass` | Merged preregistration identities and arithmetic are exact. |
| `tests/test_behavioral_comparison.py` | `test_preflight_controls_are_zero_provider_and_detect_metric_origins` | Public readback, metric, LLM-off, and corruption controls behave as frozen. |
| `tests/test_behavioral_comparison.py` | `test_attempt_record_verifier_rejects_normalized_action_corruption` | Caller/readback/action custody cannot be silently changed. |
| `tests/test_behavioral_comparison.py` | `test_run_validity_enforces_attempt_distribution_and_terminal_classes` | Every per-run gate is executable. |
| `tests/test_behavioral_comparison.py` | `test_readout_large_effect_robust_ambiguous_and_invalid` | All allowed decisions reproduce exactly. |
| `tests/test_behavioral_comparison.py` | `test_reproducer_verifies_manifest_and_saved_readout` | No provider or live database is needed to reproduce evidence. |
| `tests/test_behavioral_comparison.py` | `test_cli_refuses_live_dispatch_without_exact_cost_acknowledgement` | Accidental paid execution fails loud. |
| `tests/test_runtime_smoke.py` | `test_runner_stops_after_exact_settled_attempt_target` | Serial waiting loops cannot begin a seventeenth attempt. |

### Existing Tests

| Test Pattern | Why |
|---|---|
| `tests/test_provider_qualification.py` | Eval06 readback/custody owner remains compatible. |
| `tests/test_emergence_report.py` | Frozen paid downstream-value construct remains compatible. |
| `tests/test_runtime_smoke.py` | Default async loop scheduling remains compatible. |
| `tests/` | Full integration regression boundary. |

---

## Acceptance Criteria

- [x] `--preflight` makes zero provider calls and passes every frozen control.
- [x] Default CLI invocation and incomplete live acknowledgement refuse
      dispatch.
- [x] The optional runner target stops after exactly 16 settled attempt events
      and the corresponding action drains, with no later loop decision.
- [x] Live orchestration cannot overwrite evidence, use an unlisted pair, rerun
      a cell, exceed 448 attempts/USD 1.68, or use an unpushed/dirty revision.
- [x] Each attempt links exact caller messages/tools, provider result, receipt,
      public call record, normalized decision, action result, runtime event,
      cost, tokens, latency, and trace ID.
- [x] Scarcity and run/pair validity use the preregistered definitions.
- [x] Reserve pairs are used only in frozen order until 12 valid pairs exist or
      the 14-pair set is exhausted.
- [x] `--reproduce` verifies the manifest and exactly recomputes per-run
      metrics, validity, pairs, uncertainty, and decision without provider or
      observability-store access.
- [x] Frozen Eval07 inputs remain byte-identical.
- [x] Focused/full tests, mypy on changed executable files, Ruff, document
      coupling, and diff hygiene pass.
- [x] No Evaluation 07 provider call or spend occurs in this plan.

---

## Failure Handling

Pre-dispatch failure creates no evidence bundle unless explicitly requested by
preflight. Once live output exists, any failure preserves partial receipts,
inventory, stop reason, and manifest. The runner never tunes, retries, repairs,
or replaces a frozen cell. A material change to the preregistration requires a
new evaluation number.

---

## Completion Evidence

- The real `--preflight` CLI passed public-readback, metric, LLM-off, frozen-
  input, and four-way corruption controls with `provider_calls=0`.
- The exact-stop regression proves 16 settled attempts and 16 drained loop
  decisions; the default duration-monitor regression remains passing.
- The reproducer fixture contains 12 scheduled pairs, 24 runtime logs, and 384
  exact attempt chains. It reproduces per-run validity and the readout, rejects
  post-manifest corruption, and rejects a re-manifested schedule mutation.
- All 84 repository tests pass. MyPy passes on both changed executable modules;
  Ruff, document coupling, frozen hashes, and diff hygiene pass.
- In-progress cells checkpoint caller results plus public receipts/readback on
  every settled attempt so terminal failures retain recoverable evidence.
- Evaluation 07 was not executed: no model dispatch and no provider spend
  occurred in this plan.
