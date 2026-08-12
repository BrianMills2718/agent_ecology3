# Evaluation 07 Decision Sign-off

**Date:** 2026-08-12

**Verifier:** fresh adversarial subagent; did not run Evaluation 07

**Decision reviewed:** Treat Evaluation 07 as terminal invalid/inconclusive;
make no behavioral claim; do not rerun it; use a new evaluation number for any
further evidence.

**Evaluation:** `docs/evaluations/evidence/07_behavioral_comparison` at dispatch
revision `117ffb41a5a7cca8bee1a5c26db80a491cb50fb9`

**Verdict:** **REJECTED** — Evaluation 07's behavioral evidence is rejected.
The no-claim/no-rerun disposition is supported by gate 5; this is not a sign-off
on behavioral evidence.

## Gate Evidence

1. **Validity — FAIL.** The zero-provider preflight passed with
   `provider_calls=0`, including the positive metric value `2.0`, three
   negative LLM-off runs, corruption controls, and Evaluation 06 continuity;
   50 focused tests also passed. The full-suite command output required by the
   preregistration was not retained. More decisively, independent reproduction
   exited nonzero with `terminal partial evidence cannot satisfy complete
   reproduction`. Reverification found 189 settled events but only 188 custody
   records; `pair_06/prescribed` stopped at 13/16 attempts without a
   `simulation_stopped` event. Only one valid pair exists versus 12 required.
2. **Representativeness — FAIL.** The frozen design revalidated as 12 primary
   plus two reserve pairs, unique seeds, balanced 7/7 ordering, and no detected
   leakage. The realized evidence contains only five completed pairs plus one
   partial cell, with just one valid included pair. Prescribed/minimal rates are
   therefore unavailable and the realized sample cannot represent the
   preregistered comparison.
3. **Diagnosis — N/A.** No behavioral-underperformance diagnosis is used.
   Invalidity is established at the class level by incomplete
   execution/custody and provider error/timeout violations. The exact external
   termination cause is explicitly not claimed.
4. **Generalization — N/A.** No behavioral fix, tuning, exclusion, or rerun was
   applied.
5. **Decision — PASS.** `sha256sum -c SHA256SUMS` verified all 63 manifest
   entries, and all 57 pre-finalization raw hashes still match. The
   preregistration and Plan 09 make custody/provider/execution failure terminal,
   forbid rerunning Evaluation 07, and require a new evaluation number for
   repaired evidence. Rejecting the signal, making no prescribed-versus-minimal
   claim, and preserving the bundle is the only supported disposition.

## Required Fixes Before Any New Comparison

Reject Evaluation 07 for every behavioral inference. Do not repair or rerun it
under number 07. Any further comparison requires a newly preregistered
evaluation with fresh held-out execution and independently reproducible,
complete evidence.
