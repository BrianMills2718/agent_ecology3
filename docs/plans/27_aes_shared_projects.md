---
plan_id: "agent-ecology3#27"
dependencies: ["agent-ecology3#26"]
dependencies_reviewed: "2026-10-06"
---
# Plan #27: Shared Projects Judged by AES

**Status:** 🚧 In progress — M1 done (pilot scaffold); M2 next (kernel adapter)
**Type:** durable living plan (company-planning `durable_solo`)
**Priority:** Critical
**Blocked By:** None
**Blocks:** later scale runs on a real oracle (Plan 25 M10)

**Authority:** Brian, 2026-10-06: chose "shared projects" as the next oracle
("sure i think this might couple well with agentic engineering system
canonical"), then "proceed". Earlier the same day: the stand-in puzzle oracle is
not to be hardened, and web look-ups are a legitimate strategy with a real
oracle. This plan owns its milestones, active slice and review log;
[the roadmap](../MVP_ROADMAP.md) owns outcome and priority; [Plan 26](26_watch_the_ecology.md)
owns the views this plan reuses.
**Planning path:** `durable_solo` — one writer, continues across sessions. Two
repositories are involved: agent_ecology3 (owner of everything built here) and
`agentic-engineering-system-canonical` (AES; used as an installed tool, never
edited by this plan).
**Selected controls:** continuity = this file; coordination = single lane plus
read-only use of AES; reversibility = git-revertible PRs merged after
`make check`; external effect = none beyond the public repo; isolation = agents
edit only a sandbox clone of the pilot project, never AES or agent_ecology3.
**Artifact consumer / decision value:** Brian watches agents build one real
codebase together, paid only when AES records test evidence that a success
criterion is met, and decides whether this oracle produces cooperation worth
scaling.
**Stage / investment boundary:** local prototype; no verdict on whether
cooperation pays (that needs scale); no benchmarks.
**Last outcome-bearing update:** 2026-10-06, M1 done: tinydb pilot governed by AES; the oracle says no on the stubs and yes on the reference.

## Outcome and boundaries

**Outcome:** For Brian, change "agents paid for hidden-test passes on
independent puzzles, so they rarely trade or talk" into "agents paid by AES
evidence for advancing one shared, AES-governed codebase whose parts depend on
each other", visible in the existing feed, matrix and Living view.

**Canonical probe:** `aes init` a pilot project whose success criteria come from
a real library's own tests; 4 resident Codex agents × 20 turns edit its sandbox;
after each submitted change the kernel runs `aes evidence record` and
`aes reconcile --json`; a criterion moving INSUFFICIENT → SUPPORTED pays the
agents whose code the passing commit contains; a later change that makes the
evidence STALE without new support stops that payment. Negative case: a change
that breaks an already-supported criterion is recorded and shown, and pays
nothing.

**Review points (each a clickable UI):**
- M1: `aes status` of the pilot project and its open gaps, shown in the dashboard as the job board.
- M3: the live 4-agent run (feed, matrix, Living view).
- M4: the same run in the public replay.

**Non-goals:**
- running agents on AES canonical itself;
- editing AES (gaps in AES become issues on its repo);
- new view types (reuse Plan 26's views);
- cooperation verdicts.

**Authority limits:**
- AES changes go through AES's own plans and owners;
- the pilot project is a sandbox clone, so nothing is pushed to the upstream library.

## System model (PMI-017)

Extends [docs/model/ae3_model.yaml](../model/ae3_model.yaml) and
[ODD.md](../model/ODD.md); M2 updates both, and the drift test must stay green.

- **New entities:**
  - pilot project (sandbox git repo plus `.aes/target.yaml`);
  - success criterion (id, standing: INSUFFICIENT / SUPPORTED / REFUTED);
  - observation (id, freshness: CURRENT / STALE);
  - bounty (one per open AES gap, with an amount);
  - contribution (agent, commit, files).
- **New processes:**
  - `propose_change` (agent writes files in its sandbox branch, then submits);
  - `integrate` (kernel merges a submitted change into the pilot's main if it applies cleanly and the pilot's checks pass);
  - `judge` (kernel runs `aes evidence record` for affected verification subjects, then `aes reconcile --json`);
  - `pay` (bounty for criteria that became SUPPORTED, split by contribution; royalty when a contribution imports or calls another agent's code).
- **New events:**
  - `change_submitted`
  - `change_integrated` / `change_rejected` (with reason)
  - `aes_judged` (criterion standings before and after, observation ids)
  - `bounty_paid`
  - `royalty_paid` (existing type, new source)
- **Expected patterns** (what we look for, not verdicts):
  - agents read the open-gap list;
  - agents build on each other's modules (imports across authors);
  - messaging or payments appear when a gap needs more than one agent's code;
  - broken criteria are noticed and repaired.

```mermaid
flowchart LR
  T[".aes/target.yaml<br/>criteria"] -->|aes reconcile --json| B["Bounty board<br/>(open gaps)"]
  B --> A["Agents<br/>(resident Codex)"]
  A -->|propose_change| K["Kernel"]
  K -->|integrate + run checks| P["Pilot repo main"]
  P -->|aes evidence record| E["Observations<br/>(bound to commit)"]
  E -->|aes reconcile --json| J{"Criterion<br/>now SUPPORTED?"}
  J -->|yes| PAY["Pay contributors<br/>+ royalties"]
  J -->|no / stale| B
  PAY --> V["Feed · Matrix · Living view"]
```

## Plan

M1 scaffolds the pilot project and its AES target; M2 adds the kernel adapter
that judges and pays from AES evidence; M3 runs 4 agents live; M4 republishes
the replay; M5 (scale) waits for Brian. Details below.

## Milestones

| Milestone | Planning state | Output | Review point |
|---|---|---|---|
| M1 Pilot project scaffold | done 2026-10-06 (see Pilot facts) | One small real Python library chosen (Commit0 lite, MIT, smallest with clear module dependencies; candidates checked, not assumed); its function bodies stubbed in a sandbox repo; `aes init` with criteria = groups of the library's own tests; `aes status` shows every criterion INSUFFICIENT; a dashboard panel lists the open gaps as bounties | pilot `aes status` in the dashboard |
| M2 Kernel adapter for AES judging | fully_specifiable_now (next) | `propose_change` / `integrate` / `judge` / `pay` in the resident gateway; AES called as a subprocess on the sandbox; model YAML, ODD and drift test updated; tests with a scripted agent (no model calls) prove pay on SUPPORTED, no pay on REFUTED or STALE, royalty on cross-author import | test run + feed rows on a scripted run |
| M3 4-agent live run | conditional (after M2) | 4 Codex agents × 20 turns on the pilot, systemd unit; record criteria met, contributions per agent, cross-author imports, messages, payments | live dashboard link |
| M4 Public replay | conditional (after M3) | republish via `scripts/deploy_public_replay.sh` after the leak check (pilot library code is MIT, so code may be shown; agent notes still checked) | brianmills.dev/agent-ecology/ |
| M5 Scale | deliberately_deferred | 16+ agents, longer runs, larger library | Brian selects it |

## Pilot facts (M1, 2026-10-06)

- **Library:** tinydb from Commit0's lite split: fork https://github.com/commit-0/tinydb, upstream msiemens/tinydb, MIT licence.
- **Commits:** `base_commit` ed761a72c8c1e1cb24ca4dbcc089f35c5264d357 is Commit0's stubbed version (function bodies replaced by `pass`, 1,073 lines removed against the reference); `reference_commit` 429b27a513f0ad301632379e55667dd99865fb16 is the full implementation.
- **Module dependencies:** database → storages, table, utils; table → queries, storages, utils; queries → utils; middlewares → storages.
- **Tests:** 7 modules, 201 tests on the reference: middlewares 8, operations 14, queries 32, storages 13, tables 28, tinydb 97, utils 9. On the stubs every module fails at import (NameError `_immutable` in tinydb/utils.py, reached through tests/conftest.py).
- **Sandbox:** `~/.local/state/agent_ecology3/pilots/tinydb`, built by `uv run python scripts/build_aes_pilot.py` (outside this repo; no library code is committed here). `main` starts at ed761a72 itself, fetched shallow, so the reference commit is not reachable from the sandbox (checked: `git cat-file -e 429b27a5` fails there). Its `.venv` holds pytest 9.1.1, pytest-cov 7.1.0, pyyaml 6.0.3.
- **AES target** (project `ae3-pilot-tinydb`, actor "agent_ecology3 agents", outcome "tinydb works as its own tests specify", governed roots `tinydb/` and `tests/`), derived mechanically from `git ls-files` and accepted as `PLAN-001-TEST-MODULES` through `aes plan prepare/validate/accept`:
  - for each `tests/test_<m>.py`: `NI-<M>` → `SC-<M>` (evidence requirement `ER-<M>-01`) → `VS-<M>` with locator `tests/test_<m>.py`; M ∈ MIDDLEWARES, OPERATIONS, QUERIES, STORAGES, TABLES, TINYDB, UTILS;
  - one planned artifact per tracked governed file (20), components `CMP-LIBRARY` (tinydb/), `CMP-TEST-SUPPORT` (tests/__init__.py, conftest.py) and `CMP-<M>` per test module.
- **Test command:** AES has no command field on a verification subject ([AES #154](https://github.com/BrianMills2718/agentic-engineering-system-canonical/issues/154)), so the sandbox's committed `pilot.json` holds each subject's command, passed to `aes evidence record --command`: `.venv/bin/python -m pytest -p no:cacheprovider -o addopts= -q tests/test_<m>.py` (`-o addopts=` drops tinydb's coverage options).
- **Gate order:** the AES pre-commit hook is installed after the plan is accepted; before that every existing file is an orphan and the hook refuses the init commit ([AES #155](https://github.com/BrianMills2718/agentic-engineering-system-canonical/issues/155)).
- **Reproducibility:** rebuilding gives identical file content; commit ids differ only by AES's own `initialized_at` / `accepted_at` timestamps.
- **Gap count:** a criterion gap appears under several components in `aes reconcile --json`; the board counts each gap id once, the same rule as AES's `Reconciliation.open_gaps()`.

## Active slice: M2 — kernel adapter for AES judging

**Steps:**
1. Read `src/agent_ecology3/simulation/resident.py` (the resident gateway) and the M1 sandbox's `pilot.json`; write the model-YAML and ODD additions for the entities, processes and events in the system model above.
2. `propose_change`: an agent's files land on its own branch of a per-run clone of the pilot sandbox; `integrate` merges into that clone's `main` when it applies cleanly.
3. `judge`: for each verification subject whose dependency files changed, `aes evidence record <VS> --depends-on tests/conftest.py --command <pilot.json command>`, commit the observation, then `aes reconcile --json`; emit `aes_judged` with standings before and after.
4. `pay`: a criterion that moved to SUPPORTED pays its bounty to the contributors whose commits the supporting commit contains; REFUTED or STALE pays nothing; royalty when a contribution imports another agent's module.
5. Scripted-agent tests (no model calls) on a fresh pilot build: pay on SUPPORTED, no pay on REFUTED or STALE, royalty on a cross-author import; drift test green.

**Focused check:** the scripted run's feed shows `aes_judged` and `bounty_paid` rows whose criterion ids match `aes reconcile --json` before and after.

**Failure / containment:** if recording per change is too slow for a 20-turn run (the reference run of all 7 subjects took 13–58 s), record only the subjects whose dependency paths a change touched and say so in the review log.

## Decisions and assumptions

| Choice | Disposition | Reason / evidence |
|---|---|---|
| Next oracle = shared projects judged by AES | human_set (Brian, 2026-10-06) | quotes above |
| Pilot on a sandbox library, not AES itself | agent_decided_reversible | agents editing the governance tool is unsafe for a first run |
| Criteria from the library's own tests | agent_decided_reversible | nobody hand-writes the jobs; tests are the outside checker |
| Pay only on AES-recorded SUPPORTED evidence; stale stops pay | agent_decided_reversible | evidence is bound to the commit (AES v0.2 design) |

**Wrong when:** after M3, revisit the oracle if agents still show no cross-author imports and no messages or payments while open gaps span more than one agent's modules, or if `aes evidence record` per change makes a 20-turn run take more than 3× a CodeFlowBench run.

## Human decisions

- **M5:** whether and when to scale; not needed before M3.

## Review log

| Date | Milestone | What Brian can open | Result |
|---|---|---|---|
| 2026-10-06 | M1 | The bounty board: `uv run python -m agent_ecology3.dashboard --pilot ~/.local/state/agent_ecology3/pilots/tinydb --port 9095`, then http://127.0.0.1:9095/ (opens on the Bounties tab) | Pilot sandbox at 325a7b953eac. **Stubs** (`aes status`): `criteria: 0 supported, 7 insufficient, 0 refuted; 0 unsupported evidence requirement(s) with no route` / `observations: 0 current, 0 stale, 0 unknown, 0 unreachable; 0 superseded`. **Stubs recorded** (throwaway copy, `--stub-check`): `criteria: 0 supported, 0 insufficient, 7 refuted` (every module exits non-zero at import). **Reference** (throwaway copy `~/code/.scratch/ae3/pilot-reference-check-325a7b9`, tinydb/ restored from 429b27a5, `--reference-check`): `criteria: 7 supported, 0 insufficient, 0 refuted; 0 unsupported evidence requirement(s) with no route` / `observations: 7 current, 0 stale, 0 unknown, 0 unreachable; 0 superseded`; passes 8/14/32/13/28/97/9 = 201. Sandbox afterwards: tinydb/ and tests/ identical to ed761a72, clean tree. Board: 7 open gaps shown = 7 unique gap ids in `reconcile --json`; Playwright hovered 31 controls, 0 without a styled tooltip, standing colour blue only (no REFUTED rows), 0 page errors. Unit tests: tests/test_pilot_bounties.py 7 passed on real reconcile fixtures. |

## Exact next action

M2 step 1: read `src/agent_ecology3/simulation/resident.py` and the pilot's
`pilot.json`, then add the pilot entities, processes and events to
`docs/model/ae3_model.yaml` and `docs/model/ODD.md` with the drift test green.

## Goal text (to start this plan)

```
/goal Make agent_ecology3's resident Codex agents build one shared, AES-governed codebase and get paid only by AES evidence, per Plan 27 (docs/plans/27_aes_shared_projects.md), and show it working.

Done when:
1. M1: a pilot sandbox repo of one small real Python library (from Commit0's lite split, chosen and recorded with licence and counts) with function bodies stubbed, governed by `aes init` with one criterion per test module. `aes status` shows all criteria INSUFFICIENT on the stubs and all SUPPORTED on a reference run. The dashboard lists the open gaps as bounties.
2. M2: the resident gateway supports propose_change / integrate / judge / pay, calling AES as a subprocess. Scripted-agent tests (no model calls) prove pay on SUPPORTED, no pay on REFUTED or STALE, and a royalty on a cross-author import. docs/model is updated and its drift test passes.
3. M3: one 4-agent, 20-turn Codex run on the pilot, run as a systemd unit, recorded in Plan 27: criteria met, contributions per agent, cross-author imports, messages and payments, with a redacted bundle and a Living view screenshot.
4. M4: the run is republished at brianmills.dev/agent-ecology/ after the leak check.
5. make check on main shows its counts and exits 0. Plan 27's milestones and exact next action match what happened. Report PR numbers, run ids and counts.

Boundaries: agent_ecology3 PRs merged after make check. AES is used as an installed tool and never edited (file issues there). Agents edit only the pilot sandbox. Codex agents only, low effort. Never delete run evidence. Bundles exclude Codex folders and secrets.

Forbidden: running agents on AES canonical or agent_ecology3 itself; hand-written criteria or jobs; paying from anything but AES evidence and kernel events; any verdict on whether cooperation pays.
```
