# Evaluation 07: Prescribed-versus-Minimal Behavioral Comparison

**Preregistered:** 2026-08-11 PDT / 2026-08-12 UTC, before implementation or any Evaluation 07 model call
**Stage:** Exploratory causal pilot
**Decision owner:** Brian Mills
**Lifecycle effect:** None; AE2 and AE3 remain separately active
**Execution status:** Not implemented and not run

## Claim, decision, and non-claims

Falsifiable claim: in the frozen four-principal scarce-scrip AE3 kernel, changing
only the qualified cognition package from `prescribed` to `minimal` changes the
probability that an LLM-valid artifact creation later earns paid consumption
from another principal by at least 0.50.

The result supports one of four decisions:

1. **Large prescription effect:** proceed to component ablations when the
   observed paired rate difference is at least 0.50 and clears the frozen exact
   paired test. Report whether prescriptions enable or suppress the outcome.
2. **Prescription-robust candidate:** proceed to a larger confirmatory design
   when both conditions produce the outcome in at least 8/12 valid runs and
   their rate difference is at most 2/12. This is a candidate signal, not proof
   of equivalence.
3. **Ambiguous pilot:** revise the next design when neither rule clears; do not
   tune or rerun Evaluation 07.
4. **Inconclusive/invalid:** repair the instrument or manipulation under a new
   evaluation number when controls, scarcity, validity, custody, budget, or
   evidence invariants fail.

This evaluation cannot establish emergence, absence of a smaller prescription
effect, prompt equivalence, general population behavior, downstream utility
beyond paid reuse, which package component causes an effect, or an AE2/AE3
lifecycle change.

## System under test and treatment contract

The experimental unit is one isolated AE3 run with four principals. The source
population is the current AE3 kernel at base revision
`c65ff34591dabb5e8ea9b26a193e24250a2821d5`, the frozen Evaluation 07 config,
MiniMax M3 route, legal action schema, and held-out seeds. Provider sampling is
not seedable; pairing controls deterministic loop choices, while balanced
within-pair order limits temporal drift.

| Surface | Prescribed | Minimal | Held constant? |
|---|---|---|---|
| cognition mode | `prescribed` | `minimal` | treatment |
| prompt | `loop_prompt_variant.txt` | `loop_prompt_minimal.txt` | treatment package |
| assigned roles/objective cycle/auto-pricing | present | absent | treatment package |
| legal actions, kernel state, feedback, action gate | same | same | yes |
| fallback | prescribed package fallback | self-resource query only | treatment package; excluded from primary attribution |
| model/tools/timeouts/tokens/retries | MiniMax M3 / same / 90 s / 4096 / 0 | identical | yes |
| forced exploration | off | off | yes |
| principals and starting scrip | 4 and 2 each | identical | yes |
| mint action | available; auction delayed beyond horizon | identical | yes; prevents auxiliary scorer calls |

The package comparison is deliberate. It does not isolate prompt text from
roles, memory objectives, price nudges, or recovery policy.

## Case set, schedule, and leakage

`config/evaluations/07_behavioral_cases.json` freezes 12 primary matched pairs
(`13200`–`13211`) and two ordered reserve pairs (`13212`, `13213`). Seeds are
unique and absent from prior tracked evaluation artifacts at preregistration.
Odd pairs run prescribed first; even pairs run minimal first. A pair is the
analysis unit for condition differences.

Each run stops after the sixteenth provider **attempt** has settled and its
action has drained. The runner must not use the current successful-call counter
as the stopping boundary. It may use a reserve pair only if either cell in an
earlier pair is invalid. Both cells of an invalid pair remain in evidence and
are excluded together. Never rerun the same seed-condition cell. Stop
inconclusive if 12 valid pairs cannot be obtained from the 14 listed pairs.

The schedule was selected before Evaluation 07 output existed. Prompt, config,
case, implementation-commit, and prior Eval06 evidence hashes must be copied
into the evidence bundle before dispatch. Any overlap with prior behavioral
seeds, post-result prompt change, or unlisted case invalidates the assay.

### Frozen input identities

| Input | SHA-256 at preregistration |
|---|---|
| `config/config.behavioral_comparison_07.yaml` | `285619a6b0e7c03dc284c68dc29a7527e616940aca6fc376b6b0d063e1f7ea38` |
| `config/evaluations/07_behavioral_cases.json` | `f6b85149b7c37d38c64d266243776f3cc60a245ee76edbf665a18da440e67f09` |
| `config/prompts/loop_prompt_variant.txt` | `1c0219c4dc5dcf2aa0fb64b756546a4fa583c4e40a9f99108c7921a4b7fbc4b2` |
| `config/prompts/loop_prompt_minimal.txt` | `c1029d2fda78e6309de66d229c9a872bf17a23f11465f94106aed7a88792f96a` |
| Eval06 `SHA256SUMS` | `f1e3015781d8941fdfb9545b15d217811d32ad49ca70979fc3db26403d090e2b` |
| Eval06 signoff | `eabb724e732bfa2b946ccd538d9801241302a747f2861c9b4496b5be576c73b2` |

The one-week execution window below deliberately bounds provider drift from the
qualified Eval06 sample. It is an operational validity limit, not a claim that
the provider changes on an exact weekly schedule.

## Outcomes, judgments, and uncertainty

Primary per-run outcome:

```text
Y = 1 when llm_valid_downstream_value > 0, otherwise 0
```

The value must be scrip paid by a different principal to read or invoke an
artifact whose creation action is attributed to `decision_origin=llm_valid`.
Fallback, forced-explore, deterministic recovery, self-payment, unpaid reads,
transfers, mint awards, and repeated purchases within one run cannot create an
additional experimental unit.

For the 12 valid pairs, let `P` and `M` be prescribed/minimal positive counts;
`b` be pairs with prescribed=1/minimal=0; and `c` the reverse discordance. The
readout reports condition rates with Wilson 95% intervals and the exact
one-sided McNemar/binomial tail in the observed direction over `b+c`.

| Construct | Method and scale | Frozen threshold | Failure action |
|---|---|---|---|
| large package effect | absolute paired positive-rate difference plus exact discordance test | `abs(P-M)/12 >= 0.50`, higher condition has at least 8 positives, and one-sided exact `p <= 0.05` | otherwise do not claim a large effect |
| robust candidate | positive rate in both conditions | `P >= 8`, `M >= 8`, and `abs(P-M) <= 2` | otherwise ambiguous unless large-effect rule passes |
| scarcity manipulation | per-run observed affordability constraint | at least 8/12 included runs in each condition bind | intended decision is inconclusive |
| run engagement | exact attempt/custody accounting | 16 attempts, at least 15 LLM-valid decisions, 3–5 attempts per principal | invalidate the pair |

`scarcity_binding=1` only when retained evidence shows either an action rejected
with `error_code=insufficient_funds`, or a pre-decision state in which the
acting principal's scrip balance is below the price of at least one readable,
cross-owned paid artifact. This is computed from events plus the exact rendered
state, not inferred from the configuration label.

Secondary descriptive outcomes are paired differences in
`llm_valid_downstream_value`, cross-paid consumption events/amount, reuse-
weighted value, action-type composition, decision origins, fallback/error
rates, final balances, latency, tokens, and cost. Report all per-run values and
bootstrap intervals where useful; no secondary metric rescues the primary
decision.

This 12-pair pilot is intentionally powered only for a very large practical
effect. A null or close result cannot establish equivalence or exclude smaller
effects.

## Validity and controls

Before provider dispatch, all of the following must pass:

1. **Build adequacy:** focused runner/reproducer tests and the full repository
   suite pass from a clean pushed implementation commit.
2. **Eval06 continuity:** its evidence manifest and independent signoff verify;
   model, prompt, tool, public-readback, retry, timeout, and output-token
   surfaces are unchanged. Execution must begin by
   `2026-08-19T03:33:25Z`; otherwise use a new-number qualification.
3. **Real zero-spend readback control:** full-content positive classifies usable;
   actual metadata-only and corrupted-tool records classify custody failure.
4. **Metric positive control:** a synthetic LLM-valid write followed by a
   different principal's paid read produces `Y=1` and the exact amount.
5. **Metric negative control:** unpaid/self/fallback-created cases produce
   `Y=0`; three provider-free `llm_off` runs have zero LLM-valid decisions and
   zero LLM-valid downstream value.
6. **Corruption control:** a modified trace, raw tool payload, normalized
   action, or decision origin is rejected by the evidence verifier.
7. **Leakage and dispatch control:** hashes, schedule, balanced order, clean
   revision, maximum call count, and aggregate reservation all match before the
   first call.

A paid run is valid only with exactly 16 settled provider attempts, at least 15
LLM-valid decisions, 3–5 attempts per principal, and zero provider error,
timeout, truncation, trace failure, custody failure, cache hit, forced-explore
event, retry, or auxiliary mint-scorer call. Economic action failures such as
`insufficient_funds` are retained behavioral observations, not infrastructure
invalidity. Any config/prompt mismatch, post-target action, or missing record
invalidates the pair.

## LLM trace and evidence contract

For every attempt retain the exact rendered messages, tools, raw content and
tool-call envelope, normalized decision, action result, model/provider, task,
trace ID, timestamps, latency, token usage, marginal/charged cost, budget
receipt, public call record, and exact caller/readback equality checks. Retain
the ordered state/action event stream needed to prove creation origin, buyer,
seller, price, and scarcity binding. Evaluator fixtures and outputs remain
separate from system-under-test calls.

Evidence layout:

```text
docs/evaluations/evidence/07_behavioral_comparison/
  inputs/
  controls.json
  dispatch_plan.json
  run_inventory.json
  pairs.json
  attempts.json
  runtime_logs/<condition>/<pair_id>/
  readout.json
  reproduction.json
  SHA256SUMS
```

The future implementation must expose these no-provider commands:

```bash
python -m agent_ecology3.analysis.behavioral_comparison --evaluation 7 --preflight
python -m agent_ecology3.analysis.behavioral_comparison --evaluation 7 --reproduce docs/evaluations/evidence/07_behavioral_comparison
sha256sum -c docs/evaluations/evidence/07_behavioral_comparison/SHA256SUMS
```

## Dispatch and spend boundary

Maximum provider exposure is 14 pairs × 2 conditions × 16 attempts = **448
attempts**. Calls are serial through the existing world-execution lock, retries
are zero, and each run has a shared root-trace cap of USD 0.06. The aggregate
actual-cost ceiling is therefore **USD 1.68**. LLM-off and public-readback
controls make no provider call. Stop rather than change the model, token limit,
timeout, sample size, prompt, reserve order, per-run cap, or aggregate cap.

Do not dispatch until the implementation revision is pushed cleanly, a human
explicitly authorizes the spend/run, every preflight control passes, and the
complete dispatch plan is written. No execution is authorized by this document.

## Preregistered readout and allowed post-run work

Read all 12 valid pairs once, apply the rules above without exclusions beyond
the frozen pair-validity rule, and preserve unexpected behavior. Allowed
post-run analysis is limited to the listed secondary metrics, per-case trace
description, and clearly labeled exploratory hypotheses. Do not change a
threshold, reclassify an invalid pair, add cases, or rerun under Evaluation 07.

Before any component-ablation, confirmatory, lifecycle, publication, or thesis
decision, a fresh verifier must run `eval-decision-signoff` against the saved
artifacts. A passing runner verdict without that signoff is not decision-ready.

## Acceptance evidence grades

| Criterion | Current grade | Target before execution | Producer / verification |
|---|---|---|---|
| build adequacy | specified | passing | future Eval07 implementation tests plus `pytest -q` |
| positive/negative controls | specified | passing receipts | future `--preflight` |
| corruption/public-readback controls | specified | passing receipts | future `--preflight` |
| held-out/leakage schedule | frozen | hash match | case file and dispatch manifest |
| representative execution | not run | 12 valid matched pairs | future one-shot runner |
| full trace custody | specified | 448-or-fewer exact attempt records | verifier/reproducer |
| cost and latency | specified | complete receipts under USD 1.68 | run inventory |
| result reproduction | specified | exact saved-artifact match | future `--reproduce` |
| independent decision review | not run | `SIGNED-OFF` or rejection | `eval-decision-signoff` |

## Results

Not implemented and not run. This section may be appended only after the
frozen run and independent reproduction; the preregistered text above remains
immutable.
