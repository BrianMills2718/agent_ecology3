# Plan 11 Scarcity Control Decision Sign-off

**Decision:** Accept `0.033192` and `0.066384` as demonstrating manipulation
separation within an eight-attempt horizon, eligible only for a later
preregistered behavioral comparison.

**Verdict:** SIGNED-OFF

- **Validity — PASS.** A fresh verifier executed the real-artifact comparison,
  confirmed embedded and external checkpoint equality, verified midpoint
  hashes, found 7/7 and 8/8 successful shared-client receipts, and reran
  wrong-budget, missing-trace, non-committed, and terminal-control negatives.
- **Representativeness — PASS for the narrow claim.** One matched pair answers
  only whether the two budgets separate at dispatch eight. Model, reasoning,
  transport, MCP, retry/fallback, and shared-client revision match. The AE3
  source delta adds the frozen control route and readout without changing the
  simulation mechanism.
- **Diagnosis — N/A.** No behavioral failure is diagnosed.
- **Generalization — N/A.** No behavioral gain or generalization is claimed.
- **Decision — PASS.** Promotion stops at settings eligibility; it does not
  authorize a behavioral, causal, reliability, production, or deployment claim.

The verifier noted that route parity was independently checked but absent from
the reusable validator. The accepted implementation adds explicit model,
reasoning, transport, MCP, retry/fallback, and shared-client parity checks.
