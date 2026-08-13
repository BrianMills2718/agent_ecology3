# Plan #17: Useful Completed-Run Review

**Status:** Complete
**Type:** implementation
**Priority:** High
**Blocked By:** None
**Blocks:** Human review of the Luna Medium PoC

---

## Gap

**Current:** The completed-pair route opens authentic receipts, but presents raw state and event JSON as the primary experience.

**Target:** The existing dashboard opens with a concise, human-readable comparison of Prescribed and Minimal behavior, economic outcomes, action timelines, and study limitations. Raw evidence remains available as an advanced view.

**Why:** A review surface must answer what happened and whether the run was interesting without requiring the reviewer to interpret implementation records.

---

## References Reviewed

- `src/agent_ecology3/dashboard/server.py` - existing single dashboard and review API
- `tests/test_recoverable_poc.py` - completed-pair integration contract
- `docs/REMOVAL_04_DASHBOARD_SPRAWL.md` - approved constraint against porting AE2's panel fleet
- `agent_ecology2/src/dashboard/static/index.html` - prior information hierarchy (agents, artifacts, activity), reviewed without adopting its architecture
- Eval 15 prescribed/minimal receipts and canonical JSONL logs - authentic review data

---

## Files Affected

- `src/agent_ecology3/dashboard/server.py` (modify)
- `tests/test_recoverable_poc.py` (modify)
- `docs/plans/17_useful_run_review.md` (create)
- `docs/plans/CLAUDE.md` (modify)

---

## Plan

1. Derive a compact paired summary from each receipt and its canonical loop-decision events.
2. Make paired outcomes, action mix, and chronological decisions the default review view.
3. Keep raw state/events behind an advanced disclosure and retain the live dashboard path.
4. Verify the API, focused integration test, and the authentic Eval 15 page in a browser.

---

## Required Tests

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_recoverable_poc.py` | `test_dashboard_reopens_completed_pair_read_only` | Summary is derived from receipts/events and the review remains read-only |

---

## Acceptance Criteria

- [x] First view explains the comparison and its limitation without raw JSON
- [x] Both conditions' action sequences and failures are visible together
- [x] Economic non-results (scrip movement, transfers, mint submissions) are explicit
- [x] Raw receipts/events remain inspectable
- [x] Live controls and existing live API behavior remain intact
- [x] Focused test, full suite, and authentic browser check pass

---

## Notes

This is a bounded extension of the existing dashboard, not a port of the AE2 multi-panel frontend. The page reports descriptive evidence from one valid matched pair and must not imply a causal cognition result.

Verification: `tests/test_recoverable_poc.py` passed; full suite passed (142 tests); Ruff and mypy passed; authentic Eval 15 receipt rendered at 1280×900 with the comparison and limitations in the first viewport.
