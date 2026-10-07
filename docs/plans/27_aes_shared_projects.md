---
plan_id: "agent-ecology3#27"
dependencies: ["agent-ecology3#26"]
dependencies_reviewed: "2026-10-06"
---
# Plan #27: Shared Projects Judged by AES

**Status:** 🚧 In progress — M1 done (pilot scaffold); M2 done (kernel adapter: propose_change / integrate / judge / pay); M3 next (4-agent live run)
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
**Last outcome-bearing update:** 2026-10-07, M2 done: agents propose changes to one shared tinydb copy; AES judges every integration and bounties pay only on criteria AES records as SUPPORTED (scripted run: 7/7 criteria met, one break and repair, 240 scrip in bounties, 1 royalty).

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
| M2 Kernel adapter for AES judging | done 2026-10-07 (see review log) | `propose_change` / `integrate` / `judge` / `pay` in the resident gateway; AES called as a subprocess on the sandbox; model YAML, ODD and drift test updated; tests with a scripted agent (no model calls) prove pay on SUPPORTED, no pay on REFUTED or STALE, royalty on cross-author import | test run + feed rows on a scripted run |
| M3 4-agent live run | fully_specifiable_now (next) | 4 Codex agents × 20 turns on the pilot, systemd unit; record criteria met, contributions per agent, cross-author imports, messages, payments | live dashboard link |
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

## Active slice: M3 — 4-agent live run

**Steps:**
1. Launch as a systemd unit: `systemd-run --user --unit=ae3-plan27-m3 uv run python scripts/run_resident_ecology.py --agents 4 --turns 20 --aes-pilot ~/.local/state/agent_ecology3/pilots/tinydb --run-id plan27_m3_run1 --port 9080 --keep-serving` (Codex, low effort).
2. Watch the first two turns in the dashboard (feed, Interactions, Bounties tab reads the run's copy); stop the unit if a turn fails or a judge step takes over 120 s.
3. After the run: count criteria met, contributions per agent (`bounty_paid`), cross-author calls (`royalty_paid` with `source: pilot_function_call`), messages and transfers; redacted bundle with `scripts/run_evidence.py`; Living view screenshot; record here.

**Focused check:** every `bounty_paid` row's criterion is SUPPORTED in that integration's `aes_judged` row, and the final `aes reconcile --json` of `<run>/pilot_project` equals the last `aes_judged` standings.

**Failure / containment:** a git or `aes` failure stops the run as invalid (`ResidentKernel.fatal_error`); judge time per integration was 7–42 s in the scripted run, so 4 agents × 20 turns with ~1 integration per agent-turn costs up to ~80 judge steps (≈15–25 min of judging).

## Decisions and assumptions

| Choice | Disposition | Reason / evidence |
|---|---|---|
| Next oracle = shared projects judged by AES | human_set (Brian, 2026-10-06) | quotes above |
| Pilot on a sandbox library, not AES itself | agent_decided_reversible | agents editing the governance tool is unsafe for a first run |
| Criteria from the library's own tests | agent_decided_reversible | nobody hand-writes the jobs; tests are the outside checker |
| Pay only on AES-recorded SUPPORTED evidence; stale stops pay | agent_decided_reversible | evidence is bound to the commit (AES v0.2 design) |
| M2: agents' folders are git worktrees of a per-run clone; the kernel commits for them (authored as the agent) | agent_decided_reversible | an agent's Codex sandbox can write only its folder, not the clone's `.git`, so it cannot commit or rebase itself; authorship is set by the kernel, so agents cannot spoof it |
| M2: integrate = merge `main` into the agent's branch, then fast-forward `main` (changed from "the agent rebases") | agent_decided_reversible | the agent cannot run git writes; on conflict the merge with markers stays in its folder and it edits them out, then proposes again |
| M2: only edits to existing library files (`tinydb/`) are proposed; tests, `.aes/`, `pilot.json`, new or deleted files never are | agent_decided_reversible | an agent must not change what judges it; a new file would be an AES orphan the agents cannot plan |
| M2: every integration records all 7 subjects (changed from "only the affected ones") | agent_decided_reversible | each observation's `dependency_paths` holds nearly every library file (tinydb's `__init__` imports the package), so "affected" is all of them; scripted judge steps took 7–42 s |
| M2: contributors = agents with surviving lines (git blame at the judged commit) in the observation's library `dependency_paths`; equal split, remainder one each, most lines first | agent_decided_reversible | AES names the files the evidence depends on; blame counts only code still present. Coarse: in the scripted run every agent shared 6–7 of 8 bounties because every test imports every module. Wrong when M3 shows bounties split evenly regardless of who wrote the code that matters; then weight by covered lines |
| M2: a criterion lost and regained pays again (`regained: true`) | agent_decided_reversible (as specified) | exploitable by break-and-fix; M3 checks `bounty_paid.regained` rows for one agent breaking what it then repairs |
| M2: royalties resolve calls through imports only (`f()` imported from a library module or defined in the same file, `mod.f()`, `from .x import f`); method calls on objects are not resolved | agent_decided_reversible | matching by bare name paid royalties for `os.path.exists`, builtin `any` and `dict.pop` in the first scripted run |
| M2: each test command runs under `timeout --kill-after=5 120` | agent_decided_reversible | `aes evidence record` has no time limit, so an agent's infinite loop would hang the kernel ([AES #162](https://github.com/BrianMills2718/agentic-engineering-system-canonical/issues/162)) |
| M2: bounty 30 scrip (`--bounty-scrip`), royalty `mint.royalty_scrip` 3, both minted | agent_decided_reversible | brief's example amount; minted like checker royalties |

**Wrong when:** after M3, revisit the oracle if agents still show no cross-author imports and no messages or payments while open gaps span more than one agent's modules, or if `aes evidence record` per change makes a 20-turn run take more than 3× a CodeFlowBench run.

## Human decisions

- **M5:** whether and when to scale; not needed before M3.

## Review log

| Date | Milestone | What Brian can open | Result |
|---|---|---|---|
| 2026-10-07 | M2 | Scripted run served read-only: `uv run python scripts/run_recoverable_evaluation.py review --data-dir ~/.local/state/agent_ecology3/plan27_m2_scripted3 --port 9096`, then http://127.0.0.1:9096/ (feed, Interactions, Living view ↗). Screenshots: [feed](../evaluations/evidence/plan27_m2_scripted_feed.png), [matrix](../evaluations/evidence/plan27_m2_scripted_matrix.png), [Living view](../evaluations/evidence/plan27_m2_scripted_living.png) | `tests/test_pilot_kernel.py` 7 passed (5 drive the real `aes` CLI and git on a two-criterion fixture project; 2 unit-test the pay rule on recorded reconcile JSON); `tests/test_model_declaration.py` 5 passed. Scripted tinydb run (`scripts/run_pilot_scripted.py`, 4 scripted agents, no model calls, reference files restored from 429b27a5): 10 proposals, 7 integrated, 3 rejected (1 conflict, 2 nothing new), 7 `aes_judged`, 27 `bounty_paid` = 240 scrip (7 criteria × 30 + SC-OPERATIONS regained × 30 after alpha_2 broke `add()` and alpha_4 fixed it; the break paid nothing), 1 royalty (alpha_1's `freeze`, called from alpha_2's queries.py). Final standings 7 SUPPORTED, equal to an independent `aes reconcile --json` of the run copy. Judge seconds per integration: 41.5, 6.9, 11.8, 12.1, 29.4, 13.1, 18.7 (first one slow: tests on half-stubbed code; tests ran in parallel during some steps). Shared pilot unchanged (clean tree, HEAD 325a7b9). Playwright: 12 new matrix cells hovered, 0 without a styled tooltip, 0 page errors; feed shows `AES judged 2f9c796 by alpha_2: SC-OPERATIONS: supported → refuted`. Untested: a real Codex agent using its worktree (M3). |
| 2026-10-06 | M1 | The bounty board: `uv run python -m agent_ecology3.dashboard --pilot ~/.local/state/agent_ecology3/pilots/tinydb --port 9095`, then http://127.0.0.1:9095/ (opens on the Bounties tab) | Pilot sandbox at 325a7b953eac. **Stubs** (`aes status`): `criteria: 0 supported, 7 insufficient, 0 refuted; 0 unsupported evidence requirement(s) with no route` / `observations: 0 current, 0 stale, 0 unknown, 0 unreachable; 0 superseded`. **Stubs recorded** (throwaway copy, `--stub-check`): `criteria: 0 supported, 0 insufficient, 7 refuted` (every module exits non-zero at import). **Reference** (throwaway copy `~/code/.scratch/ae3/pilot-reference-check-325a7b9`, tinydb/ restored from 429b27a5, `--reference-check`): `criteria: 7 supported, 0 insufficient, 0 refuted; 0 unsupported evidence requirement(s) with no route` / `observations: 7 current, 0 stale, 0 unknown, 0 unreachable; 0 superseded`; passes 8/14/32/13/28/97/9 = 201. Sandbox afterwards: tinydb/ and tests/ identical to ed761a72, clean tree. Board: 7 open gaps shown = 7 unique gap ids in `reconcile --json`; Playwright hovered 31 controls, 0 without a styled tooltip, standing colour blue only (no REFUTED rows), 0 page errors. Unit tests: tests/test_pilot_bounties.py 7 passed on real reconcile fixtures. |

## Exact next action

M3 step 1: launch the 4-agent, 20-turn Codex run on the pilot as a systemd
unit (command in the active slice), then watch turns 1–2 in the dashboard.

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
