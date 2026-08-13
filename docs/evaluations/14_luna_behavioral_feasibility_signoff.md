# Evaluation 14 Decision Sign-off

**Decision:** Reject Evaluation 14 pair 01 as invalid; draw no
prescribed-versus-minimal behavioral conclusion; run no further cell until the
exposure and boundary contract is redesigned.

**Verdict:** SIGNED-OFF

- **Validity — PASS.** The independent verifier reran the provider-free design
  and cell validators. Prescribed was valid: fourteen committed dispatches,
  7/7 distribution, then one trace-free ordinal-15 rejection. Minimal was
  invalid: fifteen committed dispatches, 8/7 distribution, no rejection, and a
  completed lifecycle. Pair exposure was 29 calls versus the authorized 28.
- **Representativeness — PASS.** The only matched pair did not expose both
  conditions to the common registered boundary. Without a conforming minimal
  cell or held-out pair, behavioral differences are inseparable from unequal
  exposure; refusing comparison is required.
- **Diagnosis — PASS.** The failure is at the contract class level. The harness
  targeted fifteen attempt records while requiring record fifteen to be a
  condition-dependent scarcity rejection. Minimal therefore dispatched an
  unauthorized extra call. This is not a behavioral interpretation.
- **Generalization — N/A.** No fix or behavioral gain was evaluated. Another
  cell under the same contract would exercise a known defect.
- **Decision — PASS.** Invalidation rests on independently reproduced evidence
  and makes no cognition claim. Source custody matched clean AE3 revision
  `3afde55d` and clean accepted shared-client revision `2867157`. All 29
  receipts had zero retries; both runs declared no fallback models or MCP; all
  loop decisions recorded no gate or recovery fallback and used
  `fail_closed_no_substitute`.

## Required repair before another provider-backed cell

Enforce the authorized provider ceiling independently of condition-specific
scarcity behavior and give both cells identical committed-call exposure. Add a
pair-level pre-dispatch ceiling, then reject or suppress any cell that cannot
meet the common fourteen-call, 7/7 boundary. This sign-off does not authorize
that redesign or another execution.
