---
description: Index and lifecycle of AE3's architecture decision records
---

# Architecture Decision Records

ADRs document significant architectural decisions.

Governs: docs/adr/

## ADR Index

| # | Title | Status | Date |
|---|-------|--------|------|
| 0002 | [Keep the AE3 kernel for the trading-vs-solo comparison](0002-keep-ae3-kernel-for-trading-vs-solo.md) | Accepted | 2026-10-05 |
| 0003 | [Adopt the AES durable document set and keep ODD as the system model](0003-adopt-durable-document-set-keep-odd.md) | Accepted | 2026-10-10 |

## ADR Lifecycle

```
Proposed → Accepted/Rejected → Superseded (optional)
```

## Creating an ADR

1. Copy template to `NNNN-title.md`
2. Fill in sections
3. Add to index above
4. Get review if needed

## ADR Template

```markdown
# ADR-NNNN: Title

Status: Proposed | Accepted | Rejected | Superseded by ADR-XXXX
Date: YYYY-MM-DD

## Context
What is the issue that we're seeing that motivates this decision?

## Decision
What is the change that we're proposing and/or doing?

## Consequences
What becomes easier or harder as a result of this decision?
```

## Status Meanings

| Status | Meaning |
|--------|---------|
| Proposed | Under discussion |
| Accepted | Decision made, being implemented |
| Rejected | Decided not to do this |
| Superseded | Replaced by newer ADR |

## Related

- Full ADR pattern: `patterns/07_adr.md` in the shared
  [enforced-planning](https://github.com/BrianMills2718/enforced-planning) repository
- Binding decisions that predate this index (the 2026-02 rebuild removals):
  [Lineage and Restarts](../LINEAGE_AND_RESTARTS.md#standing-constraints-from-the-rebuild)
