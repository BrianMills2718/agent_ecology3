# Plan #9: Behavioral Comparison Execution

**Status:** Complete — terminal inconclusive/invalid
**Type:** evaluation execution
**Priority:** High
**Blocked By:** Plan #8 complete and explicit human authorization
**Blocks:** None; any further comparison requires a new evaluation number

---

## Goal

Execute the frozen Evaluation 07 prescribed-versus-minimal behavioral
comparison exactly once, retain its complete evidence bundle, reproduce the
saved readout without provider access, obtain independent decision signoff, and
publish the immutable result and failure-mode implications.

The user explicitly authorized the run and its frozen maximum actual cost of
USD 1.68. This authorization does not permit changing the model, prompts,
schedule, thresholds, attempt count, reserve policy, or rerunning any cell.

---

## Frozen Execution Contract

- Canonical implementation: `ef726682a3a3d7ea0dc89fa65b3e266deb08fcc6`
- Deadline: `2026-08-19T03:33:25Z`
- Model: `minimax/minimax-m3`
- Schedule: 12 primary matched pairs plus two ordered reserves
- Stop: exactly 16 settled provider attempts per run
- Maximum: 448 attempts and USD 1.68 actual cost
- Output: `docs/evaluations/evidence/07_behavioral_comparison/`
- No retry, tuning, replacement, exclusion outside frozen validity, or rerun

---

## Execution Steps

1. Commit and push this execution record so the dispatch revision is clean and
   durably retained by `origin`.
2. Run the full repository suite and the authentic zero-provider preflight.
   Stop before dispatch on any failure or expired deadline.
3. Invoke the one-shot live runner with exact `--acknowledge-max-cost-usd 1.68`.
4. Preserve partial evidence and stop reason on failure; never rerun a cell.
5. Verify `SHA256SUMS` and reproduce the saved readout without provider or
   observability-store access.
6. Obtain fresh execution-based `eval-decision-signoff` before using the result
   for any follow-on decision.
7. Append the immutable result, evidence links, actual spend, limitations, and
   newly observed failure modes to durable documentation; commit, push, review,
   merge, and close the claimed lane.

---

## Acceptance Criteria

- [x] Dispatch began before the frozen deadline from pushed revision `117ffb4`.
- [x] Every preflight control passed with `provider_calls=0`.
- [x] No frozen input, threshold, schedule row, model, or budget changed.
- [ ] The runner did not reach 12 valid pairs or the end of the reserve schedule;
      it ended during `pair_06/prescribed`, making the run terminal under the
      frozen failure contract.
- [x] Attempts and actual cost remained below 448 and USD 1.68: 189 settled
      attempts and USD 0.23998692.
- [ ] Complete saved-artifact reproduction is unavailable by design for this
      terminal partial bundle. The SHA-256 manifest and 57 pre-finalization raw
      hashes pass, and the reproducer fails closed rather than promoting it.
- [x] The final result preserves invalid cells and unexpected behavior without
      retrospective repair or exclusion.
- [x] A fresh independent verifier rejected the behavioral evidence and passed
      only the no-claim/no-rerun decision.
- [x] Result status, repository advice, and the new process-lifetime and atomic
      custody failure modes are reconciled across canonical documentation.

## Completion Evidence

- Terminal evidence:
  `docs/evaluations/evidence/07_behavioral_comparison/`
- Frozen decision: `inconclusive_invalid`; five completed pairs, one valid pair
  and no scarcity-binding included run.
- Integrity: 63 manifest entries pass; all 57 pre-finalization raw hashes match.
- Independent review:
  `docs/evaluations/07_behavioral_comparison_signoff.md` (`REJECTED` behavioral
  evidence; no-claim/no-rerun disposition supported).
- Focused recovery verification: nine behavioral-comparison tests pass, mypy
  passes for the changed module, and Ruff passes for the changed source/tests.

The two unmet success-path criteria above are terminal outcomes, not pending
work. Failure Handling requires preservation and a new evaluation number rather
than repair or rerun.

---

## Failure Handling

Any frozen-control, custody, provider, budget, deadline, or reproduction failure
is terminal for Evaluation 07. Preserve the generated evidence, classify the
result under the preregistered rules, and require a new evaluation number for
any repair. Do not delete output, alter evidence, or invoke `--run-live` again.
