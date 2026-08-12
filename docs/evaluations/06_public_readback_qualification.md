# Evaluation 06: Public-Readback Provider Qualification

**Preregistered:** 2026-08-11 (before any Evaluation 06 model call)
**Stage:** Exploratory instrument qualification
**Decision owner:** Brian Mills
**Lifecycle effect:** None; AE2 and AE3 remain separately active

## Claim, decision, and non-claims

Falsifiable claim: after exercising the actual public shared-client readback
contract, the repaired AE3 classifier and frozen `minimax/minimax-m3`
prompt/tool route can jointly produce at least 15 usable legal actions in 16
attempts per cognition prompt without timeout, truncation, trace loss, or
response/tool custody mismatch.

Decision:

- **Qualified:** the zero-spend positive, redaction-negative, and corruption
  controls all behave as specified; each prompt yields at least 15/16 usable
  actions; neither prompt has a timeout or truncation; and every successful
  response and tool payload exactly matches public readback.
- **Not qualified:** the controls pass but either provider condition misses a
  threshold. Do not begin a behavioral comparison.
- **Invalid assay:** a control fails; an Eval06 input/hash, case count, dispatch
  order, receipt, manifest, retry, cleanliness, or spend invariant fails. Stop
  before dispatch where possible and do not interpret provider quality.

The unit is one independent provider call. The intended population is AE3 loop
decisions rendered by the production prescribed or minimal prompt against an
ordinary deterministic state snapshot. This assay can qualify the measurement
instrument. It cannot establish emergence, downstream value, prompt
equivalence, or a prescription effect.

## Baseline, case provenance, and leakage

Evaluation 05 is historical failure-mode evidence only. Its responses and
post-run reclassification are not pooled into Evaluation 06's score.

Evaluation 06 uses a newly committed state fixture in
`config/evaluations/06_fixed_state.json`; it was not selected from Eval05 model
outputs. The cognition prompts, production strategy artifacts, production
system instruction, tool schema, model, timeouts, and decision thresholds are
unchanged. There are 32 serial calls: prescribed then minimal within each pair,
across four principal strata and four rounds. No response changes a later
prompt or state.

Known selection limits: this is one synthetic-but-production-shaped state, not
a representative simulation corpus, and provider sampling is stochastic. The
four identities and repeated rounds expose identity rendering and reliability,
not behavioral diversity. Exact duplicate prompts across rounds are deliberate
repetitions; no response is placed into later context.

Failure taxonomy:

| Class | Severity | Detection and action |
|---|---|---|
| public readback contract mismatch | critical | Control fails; invalid before spend. |
| trace or call-record loss | critical | `trace_failure`; condition cannot qualify. |
| response/tool payload mismatch or redaction | critical | `custody_failure`; condition cannot qualify. |
| timeout or output truncation | critical | Named terminal class; condition cannot qualify. |
| provider error or empty response | high | `provider_error`; at most one per condition under the usable threshold. |
| malformed or illegal action | high | Named terminal class; counts unusable. |
| legal exact action | pass | `usable_tool_action` or `usable_json_action`. |

## Zero-spend public-readback controls

Before provider dispatch, an isolated temporary SQLite store must be configured
through `llm_client.configure_logging`. The control writes synthetic call
results through the real shared-client log boundary, resolves their canonical
receipts, and reopens them through
`llm_client.observability.replay.get_call_record()`.

1. **Positive:** full-content record with one legal `ae3_action`; the untouched
   public record must classify `usable_tool_action` even though that API does
   not currently expose `content_persistence`.
2. **Known bad/redaction:** the same call logged with
   `content_persistence=metadata_only`; public readback must classify
   `custody_failure`.
3. **Corruption:** mutate a copy of the reopened full record's response or tool
   payload; it must classify `custody_failure`.

The control retains its trace IDs, receipts, raw public records,
classifications, isolated database SHA-256, and zero-cost assertion. Any
failure stops before model dispatch.

## Metrics and readout

| Construct | Method | Scale / threshold | Uncertainty | Failure action |
|---|---|---|---|---|
| public contract validity | Three real persistence/readback controls | 3/3 exact expected classes | Deterministic | Invalid assay before spend |
| usable action reliability | Production intent parser after exact custody | Separately per prompt, at least 15/16 | Descriptive small-sample rate; report every case | Not qualified |
| hard transport reliability | Receipt/error classification | Zero timeout and zero truncation per prompt | Report counts and max latency | Not qualified |
| trace completeness | Exactly one receipt and call record per trace | 16/16 per prompt | Deterministic identity check | Invalid or not qualified per missing evidence |
| custody | Exact caller/readback response and tool equality | Every successful call | Deterministic equality | Not qualified |
| cost | Sum canonical receipt cost | At most USD 0.40 configured aggregate ceiling | Report actual; no extrapolation | Invalid if cap contract breached |

No confidence or equivalence claim is planned. Conditions are not compared to
each other; both must independently clear the same operational floor.

## Frozen provider and execution matrix

| Setting | Frozen value |
|---|---|
| model | `minimax/minimax-m3` |
| prompts | committed prescribed and minimal production prompts |
| state | `config/evaluations/06_fixed_state.json` |
| retries | `0` |
| timeout | `90` seconds per call |
| maximum output | `4096` tokens |
| calls | `16` per prompt, `32` total |
| order | prescribed/minimal alternating; four principals x four rounds |
| dispatch | serial only |
| root budget | USD `0.20` per condition |
| aggregate configured ceiling | USD `0.40` |
| budget reservation | USD `0.01` per dispatch |
| output | `docs/evaluations/evidence/06_public_readback_qualification/` |

No fallback model, retry, response-repair call, replacement case, concurrent
dispatch, or threshold change is allowed. Stop on budget exhaustion.

## Full-trace and artifact contract

Before call 1, write the control evidence, exact Git revision/cleanliness,
input hashes, effective configs, held-out state, both prompts, rendered
messages, tool schema, ordered case plan, and SHA-256 hashes. For every call,
retain the caller-visible syscall result, canonical receipt, public call
record, classification, parsed action, usage, finish reason, latency, cost, and
trace ID. Finish with condition summaries and `SHA256SUMS` over the bundle.

No API keys, environment dumps, or provider SDK objects are retained. The
saved artifacts must reproduce the summary without another model call.

Execution is permitted only from a clean pushed revision with an explicit
`--evaluation 6 --run-live` acknowledgement. Results are appended here after
the one allowed run. A passing result is handed to `eval-decision-signoff`
before any behavioral evaluation begins.

## Acceptance evidence before dispatch

| Criterion | Current grade | Target | Producer / verification |
|---|---|---|---|
| preregistration and frozen hashes | planned | committed | Git revision plus runner hash preflight |
| actual public-readback positive control | planned | pass | isolated-store control test and saved receipt |
| redaction/corruption negative controls | planned | pass | isolated-store control test and saved records |
| 32-case held-out plan / no leakage | planned | pass | case-plan hashes and state differs from Eval05 |
| async runtime and classifier build adequacy | planned | pass | Plan #6 required tests and full suite |
| trace/cost/latency evidence | planned | complete | saved receipts and public records |
| result reproduction | planned | pass | recompute summary and verify `SHA256SUMS` |

## Results

Not run.
