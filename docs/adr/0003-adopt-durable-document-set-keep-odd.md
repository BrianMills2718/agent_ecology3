---
description: Adopt the AES durable document set in AE3 and keep ODD.md as the system-model prose instead of adding an ARCHITECTURE.md
---

# ADR 0003: Adopt the AES durable document set and keep ODD as the system model

**Status:** Accepted (agent decision under Brian's delegation of high-confidence, reversible calls)
**Date:** 2026-10-10
**Plan:** AES plan aes-durable-docs, milestone M5

Governs: .agentic/repo.yaml, docs/model/trace.yaml, RULE-MODEL-MATCHES-EVENTS

## Question

AES asks every Brian-owned repository to declare a fixed set of durable
documents (goal, requirements, system model with a checked trace, decisions,
plans) in `.agentic/repo.yaml`. Which existing AE3 documents fill those slots,
and does AE3 need a new `ARCHITECTURE.md` for the system model?

## Decision

- Goal: new `docs/architecture/GOAL.md` (arc42 Introduction and Goals plus the
  AES extension fields), drawn from the roadmap, Plan 24 and the lineage page.
- Requirements: new `docs/architecture/REQUIREMENTS.md`, one `REQ-` section per
  operator-visible requirement, each with a success and a disproof condition.
- System model prose: the existing `docs/model/ODD.md`. AE3 is an agent-based
  simulation, and ODD (Grimm et al.) is the standard description format for
  those; the company-planning system-model reference says simulations keep ODD.
  ODD.md was rewritten on 2026-10-07 against the code, and
  `docs/model/ae3_model.yaml` is already checked against the emitted events by
  `tests/test_model_declaration.py`. A second architecture page would duplicate
  it and drift.
- Trace: new `docs/model/trace.yaml`, naming for each kernel rule one owner file,
  the tests that check it and the decision behind it.
- Decisions: `docs/adr/`. Plans: `docs/plans/`. Glossary and catalog are
  declared not applicable with reasons in `.agentic/repo.yaml`.

## Consequences

- The durable-docs checker (company-planning `durable_docs_check.py`) can run
  on AE3 and fail when a traced owner changes without the trace being reviewed.
- Changing a kernel rule now means updating ODD.md section 6 and the matching
  trace entry in the same change.

## Wrong if

A change to a traced owner file (for example `src/agent_ecology3/world/mint.py`)
lands with ODD.md and trace.yaml left stale twice in a row, or a reader starting
at `wiki/index.md` cannot find which file enforces a rule from ODD section 6.
Either means keeping the trace separate from ODD is not working and the trace
should be generated from ODD or folded into it.
