# Plan #6: Public-Readback Provider Qualification

**Status:** Complete
**Type:** implementation
**Priority:** High
**Blocked By:** None
**Blocks:** Fresh prescribed-versus-minimal behavioral evaluation

---

## Gap

**Current:** Plan #5 repaired the async runtime and retained exact provider
responses. Evaluation 05 nevertheless returned `not_qualified` because its
classifier expected a SQLite persistence-policy field that
`llm_client.observability.replay.get_call_record()` does not expose.

**Target:** Exercise the actual public write/receipt/readback chain with
positive, redaction-negative, and corruption controls before spend, then run a
new-number qualification on a held-out fixed-state fixture under the unchanged
provider thresholds.

**Why:** Reusing Evaluation 05's responses as a passing result would be
post-result reclassification. A fresh assay can validate the repaired decision
path without modifying Evaluation 05 or starting the behavioral comparison.

---

## References Reviewed

- `docs/evaluations/05_provider_tool_qualification.md` - immutable failed
  verdict, post-run diagnostic, and exact API-shape defect.
- `src/agent_ecology3/analysis/provider_qualification.py` - frozen classifier,
  case builder, trace readback, evidence writer, and serial dispatch.
- `tests/test_provider_qualification.py` - deterministic classifier controls.
- `llm_client/observability/replay.py:get_call_record` - actual public record
  shape: decoded messages, response, and tool calls without the SQLite
  persistence-policy column.
- `llm_client/observability/query.py:get_llm_call_receipts` - canonical
  trace-to-call receipt lookup used to reopen one exact call.
- `llm_client/io_log.py:log_call` - real local persistence boundary used by the
  zero-spend control.
- `docs/LINEAGE_AND_RESTARTS.md` - recurring experiment-instrument failure
  modes and the prohibition on treating plumbing as thesis evidence.

---

## Files Affected

- `src/agent_ecology3/analysis/provider_qualification.py`
- `tests/test_provider_qualification.py`
- `config/config.provider_qualification_06.yaml` (create)
- `config/evaluations/06_fixed_state.json` (create)
- `docs/evaluations/06_public_readback_qualification.md` (create; append results
  only after the frozen run)
- `docs/evaluations/evidence/06_public_readback_qualification/` (generated only
  after the frozen run)
- `docs/plans/06_public_readback_qualification.md`
- `docs/plans/CLAUDE.md`
- coupled operator and lineage docs if the result changes their status

---

## Plan

1. Preregister Evaluation 06, its held-out state, unchanged provider settings,
   thresholds, evidence contract, and no-rerun rule before any model call.
2. Add a real zero-spend integration control that writes synthetic full-content
   and metadata-only calls to an isolated shared-client SQLite store, reopens
   them through public receipt/readback APIs, and runs the production
   classifier without injecting missing fields.
3. Require the positive record to pass and the redaction/corruption records to
   fail before creating a provider dispatch plan.
4. Generalize the one-shot runner to an explicit Evaluation 06 specification;
   preserve Evaluation 05 inputs and evidence unchanged.
5. Run focused and full local gates, commit and push a clean instrument
   revision, then execute Evaluation 06 exactly once if every preflight passes.
6. Preserve the full trace/evidence bundle and append the frozen result. Before
   a passing result authorizes behavioral work, obtain `eval-decision-signoff`
   against the saved evidence.

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|---|---|---|
| `tests/test_provider_qualification.py` | `test_public_readback_control_accepts_exact_full_record` | Actual public readback passes without a synthesized persistence key. |
| `tests/test_provider_qualification.py` | `test_public_readback_control_rejects_metadata_only_record` | The actual redacted readback shape is rejected as custody failure. |
| `tests/test_provider_qualification.py` | `test_public_readback_control_rejects_corrupted_record` | A mutated reopened response/tool payload cannot pass custody. |
| `tests/test_provider_qualification.py` | `test_evaluation_06_uses_held_out_inputs_and_output` | Eval06 cannot reuse Eval05's state, evidence directory, or preregistration identity. |
| `tests/test_provider_qualification.py` | `test_live_runner_stops_before_dispatch_when_public_control_fails` | Control failure makes zero provider calls and writes an invalid-assay preflight result. |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|---|---|
| `tests/test_provider_qualification.py` | Existing terminal classes, thresholds, and frozen case order remain intact. |
| `tests/test_runtime_smoke.py` | Native async syscall accounting and drain behavior remain intact. |
| `tests/test_config_and_actions.py` | Frozen configuration and action parsing remain compatible. |
| `tests/test_scarcity_matrix.py` | Existing evaluation orchestration remains compatible. |

---

## Acceptance Criteria

- [x] Evaluation 06 inputs and readout are committed before any Eval06 model
      call.
- [x] The zero-spend control uses the actual public receipt/readback APIs and
      proves both acceptance and rejection behavior in an isolated store.
- [x] A failed control stops before provider dispatch and is preserved as an
      invalid assay rather than silently falling back.
- [x] The held-out case plan, messages, tool schema, effective config, control
      receipts, provider receipts, call records, costs, and hashes are retained.
- [x] Evaluation 06 runs at most once with 32 serial calls, no retry, and an
      aggregate configured ceiling of USD 0.40.
- [x] Focused tests, full tests, changed-file type checking, document coupling,
      evidence-manifest validation, and diff hygiene pass.
- [x] Evaluation 05 remains byte-for-byte unchanged; no behavioral comparison
      begins without a passing Evaluation 06 and independent decision signoff.

---

## Failure Handling

Any public-readback control failure, frozen hash mismatch, dirty dispatch
revision, missing receipt/call record, retry, concurrent dispatch, timeout,
truncation, custody mismatch, or spend-cap breach is visible in the evidence.
Pre-dispatch failures make no provider call. A completed non-passing or invalid
assay is not tuned or rerun under Evaluation 06.

---

## Completion Evidence

- Preregistration was pushed at `aa128e7`; the executable instrument was pushed
  at `4b4a86c` before the first Eval06 control/provider timestamp.
- The real isolated public-readback control passed its full-content positive,
  metadata-only negative, and corrupted-record negative cases with zero
  provider calls and zero cost.
- Evaluation 06 ran once: prescribed 16/16 usable; minimal 15/16 usable with one
  `illegal_action`; zero timeout, truncation, trace, custody, or provider
  failures; actual cost USD 0.03988458; frozen verdict `qualified`.
- The evidence manifest verifies and independently reproduces 32/32 exact
  messages, response content, response-tool payloads, traces, call records, and
  stored classifications.
- Independent adversarial signoff: `SIGNED-OFF` for instrument qualification
  and behavioral design/preregistration only. It explicitly rejects emergence,
  prompt-equivalence, prescription-effect, downstream-value, or representative
  population claims from this assay.
- Local verification: 76 full-suite tests and 63 plan-required tests passed;
  focused changed-file mypy, Ruff, document coupling, and diff hygiene passed.
