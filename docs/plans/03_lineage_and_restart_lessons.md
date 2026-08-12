# Plan #3: Repository Lineage and Restart Lessons

**Status:** ✅ Complete

**Verified:** 2026-08-12T00:29:04Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-08-12T00:29:04Z
tests:
  unit: 51 passed in 1.41s
  e2e_smoke: skipped (--skip-e2e)
  e2e_real: skipped (--skip-real-e2e)
  doc_coupling: passed
commit: 80c34e1
```
**Type:** design
**Priority:** High
**Blocked By:** None
**Blocks:** A future decision on whether AE3 formally supersedes AE2

---

## Gap

**Current:** AE3 records its six approved removals from AE2, and AE2 records
many simulation lessons, but no short current document compares all three
repositories or separates documented restart decisions from inferred causes.

**Target:** One README-linked lineage document explains each repository's
scope, the evidence behind both restarts, recurring failure modes, present
risks, and the unresolved lifecycle decision between AE2 and AE3.

**Why:** Without this boundary, a future contributor can repeat AE2's
architecture growth, mistake plumbing/KPI checks for emergence evidence, or
incorrectly treat repository numbering as lifecycle authority.

---

## References Reviewed

- `README.md` - AE3 scope, commands, experimental claims, and documentation index.
- `docs/REWRITE_SCOPE.md` - approved AE2-to-AE3 keep/add/remove boundary.
- `docs/REMOVAL_SEQUENCE.md` and `docs/REMOVAL_01_*.md` through
  `docs/REMOVAL_06_*.md` - detailed structural reasons for the clean rebuild.
- `docs/IMPLEMENTATION_BASELINE.md` - AE3 baseline and historical experiment record.
- `docs/CHATGPT_FULL_CONTEXT.md` - rewrite rationale, empirical claims, and open uncertainties.
- `agent_ecology2/docs/SIMULATION_LEARNINGS.md` at commit `33bbb6d` - observed
  agent paralysis, stale guidance, and failed cooperation smoke runs.
- `agent_ecology2/docs/V1_ACCEPTANCE.md` at commit `33bbb6d` - AE2's plumbing-oriented V1 gate.
- `agent_ecology` at commit `7209207` - executable heuristic prototype and sweep harness.
- Project Meta `PROJECT_GRAPH.json` - lifecycle authority for all three repositories.

---

## Files Affected

- `README.md` (modify)
- `docs/LINEAGE_AND_RESTARTS.md` (create)
- `docs/plans/03_lineage_and_restart_lessons.md` (create)
- `docs/plans/CLAUDE.md` (modify)

---

## Plan

### Steps

1. Record the reviewed revision and evidence class for every material claim.
2. Compare repository scope, scale, runnable evidence, and intended use.
3. Document both transitions without inventing a failure narrative where no
   historical decision record exists.
4. Record recurring failure modes and AE3 watch items.
5. Link the lineage record from the README and plan index.

---

## Required Tests

### New Tests (TDD)

No production behavior changes. Validate documentation paths and immutable
GitHub evidence links with a focused script.

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `pytest -q` | Establish the reviewed AE3 baseline; production code is unchanged. |
| `git diff --check` | Reject malformed Markdown whitespace. |

---

## Acceptance Criteria

- [x] A fresh reader can distinguish AE1, AE2, and AE3 without reading the full histories.
- [x] Each restart cause is labeled documented, observed, or inferred.
- [x] The AE2 behavioral readout gap is distinct from implementation/test health.
- [x] AE3 risks and the unresolved AE2/AE3 lifecycle decision are explicit.
- [x] README and plan-index links resolve.

---

## Notes

This plan does not change Project Meta lifecycle records. AE2 and AE3 remain
separately active until the owner makes that portfolio decision.
