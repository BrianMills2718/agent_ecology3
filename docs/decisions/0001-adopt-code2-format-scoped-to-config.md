# 0001: Adopt the code2 format, scoped to the configuration loader

Status: Accepted
Date: 2026-11-17
Source: inferred by agent, 2026-11-17: adopting the format for this repository (Brian, 2026-11-17: "option B is what i want")

## Context

Active vision parts adopt the code2 repository format now. This repository already has an ODD system model, plans and ADRs (`docs/adr/`), an older `.agentic/` document system, and a long test suite.

## Decision

Add the code2 format around one capability that already has working code and tests: strict configuration loading (`src/agent_ecology3/config.py`, spec `strict-config`). Lockstep scans only `src/agent_ecology3` for `Implements:` lines. `make check` now runs Lockstep, OpenSpec validation, the import contract and the two config test files (seconds). The former `make check` (all tests plus mypy) is kept unchanged as `make full`. Existing documents, tests and behavior are untouched; the older `.agentic/`, `meta-process.yaml` and `docs/adr/` systems are left in place.

## Consequences

- `make check` is a narrower gate than before; the full suite is `make full`, and AGENTS.md and README.md name both.
- Only the config capability is covered by Lockstep; other capabilities join when next changed.
- Two systems of decision records exist (`docs/adr/` and `docs/decisions/`) until the older one is retired.

## Wrong if

The scoped `make check` lets a regression through that `make full` would have caught and nobody runs `make full`; or the older documentation system is retired, making this record the only one.
