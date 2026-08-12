# EVAL-DECISION SIGN-OFF

**Decision:** Accept Evaluation 06 as qualifying the AE3 provider/prompt/tool
measurement instrument, and unblock design/preregistration—but not execution—of
a fresh prescribed-versus-minimal behavioral evaluation.

**Evaluation:** `docs/evaluations/06_public_readback_qualification.md` and
`docs/evaluations/evidence/06_public_readback_qualification/`

**Dispatch commit:** `4b4a86c70b2b7d82b64a9bdb99ca9c887f4e4592`

**Verdict:** `SIGNED-OFF`

## Gate 1 — Validity: PASS

Fresh execution of `_run_public_readback_control_isolated` returned
`passed=True`, `provider_calls=0`, and `zero_cost=True`. Observed classes were
`positive=usable_tool_action`, `redaction=custody_failure`, and
`corruption=custody_failure`; stored policies were `positive=full` and
`redaction=metadata_only`.

`sha256sum -c SHA256SUMS` returned `OK` for every Eval06 evidence file. An
independent 32-row reproduction reported zero errors and 32/32 exact trace,
receipt, readback, response, tool-payload, and classification matches. It
recomputed prescribed at 16/16 usable, minimal at 15/16 usable plus one illegal
action, no timeout/truncation/trace/custody failure, cost USD 0.03988458, and
verdict `qualified`. Frozen current and copied-input hashes matched.

Focused build adequacy:

```text
.venv/bin/python -m pytest -q tests/test_provider_qualification.py tests/test_runtime_smoke.py --tb=short
........................................ [100%]
40 passed
```

## Gate 2 — Representativeness: PASS within the proposed decision

Execution confirmed the Eval05 and Eval06 fixtures are byte-distinct:
Eval05 SHA-256 `0cd6a09c...f80ff9e`; Eval06
`c1792e2c...6acb9a`. State differs in turn 3 to 7, balance 6 to 9, and
artifact count 2 to 3. Eval06 made 32 new calls over four principals and four
rounds; no Eval05 response was pooled.

This is adequate only for instrument qualification. The single synthetic,
production-shaped state is not representative of AE3 behavioral or general
populations. The signoff excludes emergence, prompt-equivalence,
prescription-effect, downstream-value, and general-population claims.

## Gate 3 — Diagnosis: PASS

Re-execution over immutable Eval05 evidence found its recorded
`custody_failure` count was 32, the public readback omitted
`content_persistence` on 32/32, response equality held on 32/32, and tool
equality held on all 31 successful tool calls. The repaired classifier
reproduced 31 usable tool actions and one provider error.

The executed code diff shows that Eval05's unconditional requirement for the
unexposed field was replaced by an optional-field check plus exact response and
tool comparisons. Eval05's manifest also verified. The diagnosis is therefore
a class-level public-readback contract mismatch, not an instance anecdote.

## Gate 4 — Generalization: PASS

The repaired classifier reproduced all 32 classifications on the new Eval06
calls and distinct held-out fixture, including the minimal case-12 rejection.
The public-readback positive, metadata-redaction, and corrupted-tool paths all
generalized as expected. No timeout, truncation, trace, custody, or provider
regression appeared, and the focused provider/runtime suite passed 40/40.

## Gate 5 — Decision: PASS

Git verification showed preregistration hash
`ee93182b...e730` at pushed commit `4b4a86c...`, committed at
2026-08-12T03:32:47Z before the first retained Eval06 timestamp at
2026-08-12T03:33:25Z. The frozen rules already required all three controls,
at least 15/16 usable per prompt, zero timeout/truncation, exact custody, and
spend below USD 0.40. The reproduced result clears those rules without a
threshold change.

The decision stops at instrument qualification and behavioral design/
preregistration, so it does not exceed the evidence.

## Required fixes

None for the proposed decision. Preserve this signoff and the evidence bundle
durably. Do not execute or make behavioral claims from a subsequent evaluation
until its fresh design and preregistration are separately adopted.
