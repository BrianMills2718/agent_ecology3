# Plan #20: Single-Run Archive Reopen

**Status:** Complete
**Type:** prototype vertical
**Priority:** Critical
**Blocked By:** None
**Blocks:** Dashboard launch of another bounded run

## Gap

**Current:** Completed review assumes a directory containing the two hard-coded
`prescribed` and `minimal` cells. The canonical Plan 19 run remains coupled to
its original worker for convenient dashboard access.

**Target:** A fresh, model-free review process accepts either one preserved run
directory or a directory of preserved runs, lists valid receipts, and opens the
selected run read-only in the existing Ecosystem dashboard. Matched-pair review
continues to expose Comparison.

**Why:** This is the first missing boundary between the one-off MVP and a
repeatable local workbench.

## References Reviewed

- `docs/MVP_ROADMAP.md` - canonical outcome, order, success criterion, and YAGNI boundary
- `scripts/run_recoverable_evaluation.py` - current hard-coded matched-pair review entry point
- `src/agent_ecology3/dashboard/server.py` - existing receipt projection and UI
- `tests/test_recoverable_poc.py` - matched-pair preservation contract
- `CLAUDE.md` - repository workflow and coordination rules

## Files Affected

- `scripts/run_recoverable_evaluation.py` (modify)
- `src/agent_ecology3/dashboard/server.py` (modify)
- `tests/test_recoverable_poc.py` (modify)
- `docs/plans/20_single_run_archive_reopen.md` (create)
- `docs/plans/CLAUDE.md` (modify)
- `docs/MVP_ROADMAP.md` (modify)

## Implementation Order

1. Discover and validate either a direct receipt directory or immediate receipt-bearing children.
2. Serve the discovered inventory through the existing `review_runs` seam.
3. Mark Comparison available only for the preserved `prescribed`/`minimal` pair.
4. Keep Ecosystem and Evidence available for every preserved run and preserve matched-pair review.
5. Shut down the original Plan 19 worker and reopen its receipt in a fresh process.

## Required Tests

| Test | What it verifies |
|---|---|
| Single-run discovery and API review | One receipt is listed and projected read-only without a comparison |
| Invalid direct receipt | Malformed or incomplete custody fails visibly |
| Existing matched-pair test | Comparison and both condition selectors remain available |
| Fresh browser journey | Plan 19 reopens with 14 actions, final balances, artifacts, lifecycle, and evidence |

## Acceptance Criteria

- [x] A direct Plan 19 run directory starts a fresh read-only review process.
- [x] `/runs` lists the preserved run and the dashboard opens it in Ecosystem.
- [x] Dashboard/API values reconcile to 14 actions, final balances 104/95, 23 final artifacts, and completed lifecycle.
- [x] Starting review makes zero model calls.
- [x] Existing prescribed/minimal matched-pair Comparison remains available.
- [x] Missing or malformed receipt custody fails visibly.

## Non-goals

- Launching a run, scenario authoring, graphs, databases, deployment, authentication, or production hardening.
- Changing the receipt schema or reconstructing a mutable `World`.

## Likely Failure Modes

- A direct run directory is mistaken for a library root and reported missing.
- A malformed receipt is silently omitted or fails only after the browser loads.
- Single-run review calls the matched-pair summary and fabricates a comparison.
- The change strands the existing matched-pair Comparison or live dashboard controls.
- Review accidentally invokes runner or model code instead of reading custody.

## Completion Evidence

- Original Plan 19 worker PID 82728 shut down through the graceful control path.
- A fresh process from pushed revision `bf00c39` served the direct Plan 19
  directory on port 9019 with no runner or model-dispatch seam.
- `/runs`, `/operator-state`, `/state`, and `/events` reconciled the preserved
  run as read-only, completed, 14 decisions, balances 104/95, and 23 final
  artifacts. The preserved provider dispatch count remained 14.
- Fresh Chromium at 1440×900 opened Ecosystem, switched to Evidence and back,
  and started replay. Comparison was absent, the selector was labeled Run, and
  the browser reported no console errors or failed requests.
- The complete pytest suite and doc-code coupling check passed. Mypy reported
  26 existing errors across seven unchanged files; it reported no error in the
  changed dashboard source.
