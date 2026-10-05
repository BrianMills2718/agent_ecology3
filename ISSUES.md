# Issues

Observed problems, concerns, and technical debt. Items start as **unconfirmed**
observations and get triaged through investigation into confirmed issues, plans,
or dismissed.

**Last reviewed:** 2026-10-05

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

(Add observations here with enough context to investigate later.)

---

## Monitoring

(Items confirmed as real but not yet urgent. Include trigger conditions.)

---

## Confirmed

(None.)

---

## Resolved

| ID | Description | Resolution | Date |
|----|-------------|------------|------|
| ISSUE-001 | Paid evaluation worker was not session-durable (Evaluation 07 ended mid-run; settlement and custody persistence were not atomic) | Plan 10 (WU-10-05) added a detached supervisor, an atomic per-attempt checkpoint (`dispatching -> provider_settled -> applying -> committed`), and replay of a settled response instead of a new provider call; Plan 22 moved durable workers off removable worktree paths. Later paid runs (Evaluations 14-15, Plans 19-24) used that worker (`scripts/run_recoverable_evaluation.py`). | 2026-10-05 |

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
