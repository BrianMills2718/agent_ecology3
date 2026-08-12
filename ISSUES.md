# Issues

Observed problems, concerns, and technical debt. Items start as **unconfirmed**
observations and get triaged through investigation into confirmed issues, plans,
or dismissed.

**Last reviewed:** 2026-08-12

---

## Status Key

| Status | Meaning | Next Step |
|--------|---------|-----------|
| `unconfirmed` | Observed, needs investigation | Investigate to confirm/dismiss |
| `monitoring` | Confirmed concern, watching for signals | Watch for trigger conditions |
| `confirmed` | Real problem, needs a fix | Create a plan |
| `planned` | Has a plan (link to plan) | Implement |
| `resolved` | Fixed | Record resolution |
| `dismissed` | Investigated, not a real problem | Record reasoning |

---

## Unconfirmed

(Add observations here with enough context to investigate later)

### ISSUE-001: (Title)

**Observed:** (date)
**Status:** `unconfirmed`

(What was observed. Why it might be a problem.)

**To investigate:** (What would confirm or dismiss this.)

---

## Monitoring

(Items confirmed as real but not yet urgent. Include trigger conditions.)

---

## Confirmed

### ISSUE-001: Paid evaluation worker is not session-durable

**Observed:** 2026-08-12
**Status:** `confirmed`

Evaluation 07's paid worker ended without graceful finalization after 189
settled attempts. Raw events and per-attempt checkpoints survived, but the
world/scheduler process did not, so the frozen no-rerun contract prohibited
recovery of the partial seed-condition cell. Separately, a cancelled settled
attempt in `pair_02/prescribed` produced an event without a linked
loop-decision/custody record.

**Required before another paid behavioral assay:** use a durable process
supervisor independent of the interactive agent session; make settlement,
decision/failure classification, cost, and custody persistence atomic; and
prove recovery from cancellation at each persistence boundary without
repeating a provider attempt. Any repaired assay must use a new evaluation
number. See `docs/evaluations/07_behavioral_comparison.md` and
`docs/LINEAGE_AND_RESTARTS.md`.

---

## Resolved

| ID | Description | Resolution | Date |
|----|-------------|------------|------|
| - | - | - | - |

---

## Dismissed

| ID | Description | Why Dismissed | Date |
|----|-------------|---------------|------|
| - | - | - | - |

---

## How to Use This File

1. **Observe something off?** Add under Unconfirmed with context and investigation steps
2. **Investigating?** Update the entry with findings, move to appropriate status
3. **Confirmed and needs a fix?** Create a plan, link it, move to Confirmed/Planned
4. **Not actually a problem?** Move to Dismissed with reasoning
5. **Watching a concern?** Move to Monitoring with trigger conditions
