---
description: What Agent Ecology 3 is for, the bet it exists to test, what would disprove that bet, and the repository it was rebuilt from
---

# Agent Ecology 3: goal and thesis

Drawn from `README.md`, `docs/MVP_ROADMAP.md` (outcome, current goal, YAGNI
list), `docs/plans/24_external_score_vs_solo.md` (thesis and its test),
`docs/LINEAGE_AND_RESTARTS.md` (restart reason and standing constraints) and
`docs/model/ODD.md` (purpose and patterns).

## Introduction and Goals

### Requirements Overview

AE3 is a local workbench where Brian launches small, bounded economies of LLM
agents under scarce resources, watches who did what and why value moved, and
reopens any finished run read-only. Agents spend scrip (the in-world currency),
write artifacts and sell reads of them to each other, and earn new scrip only
from an outside checker that pays for solved coding tasks. The requirements,
each with a success and a disproof condition, are in
[REQUIREMENTS.md](REQUIREMENTS.md). The rules that enforce them, with their
owner files and tests, are in the system model ([ODD.md](../model/ODD.md),
[trace.yaml](../model/trace.yaml)).

### Quality Goals

- **Fail loud.** An authentic run stops and is recorded invalid on any model,
  transport, schema or selected-action failure; nothing is substituted for a
  failed decision (`AGENTS.md` design principle 2, Plan 22).
- **Truth before polish.** Every dashboard view reads only the run's
  `events.jsonl` and `run_receipt.json`; a test keeps the declared event list
  identical to the events the code writes (`tests/test_model_declaration.py`).
- **Reopenable evidence.** A preserved run reopens in the dashboard with zero
  model calls from its committed evidence bundle.
- **Simple until evidence demands more.** One typed config that rejects unknown
  keys, one action vocabulary, one bounded dashboard
  ([standing constraints](../LINEAGE_AND_RESTARTS.md#standing-constraints-from-the-rebuild)).

### Stakeholders

- Brian, the operator who launches runs, reads the dashboard and decides the
  next experiment.
- Coding agents (Claude Code and Codex) that build and maintain the workbench.
- The resident agents themselves (long-lived Codex sessions acting only through
  the kernel's `ae3_action` tool), whose behavior the workbench records.

## North star (AES extension)

Change a one-off, CLI-oriented agent simulation into a repeatable local
workbench where Brian can launch bounded ecologies, understand who did what and
why value moved, reopen completed runs, compare useful runs, and explore richer
scenarios without editing source code (`docs/MVP_ROADMAP.md`, "Outcome and
operating bias"). Current goal (Brian, 2026-10-05): get the system working and
the agents behaving intelligently so it can scale.

## Thesis (AES extension)

Agents with scarce resources and no assigned roles produce more together than
the sum of what they could produce alone, and this shows only at scale and over
long horizons (AE2 README, restated in Plan 24 and the roadmap). AE3 tests it
with value from outside the run: new scrip comes only from a checker that runs
hidden tests, and cooperation can pay only through it (royalties for reused
helpers, posted read prices). Claims about a run are read from where its truth
is written, the append-only event log and the code-checked model, never from
prompts or prose summaries (AES-CTX-004, truth lives where it is edited).

## Thesis disproof (AES extension)

At a scale Brian accepts as testing the thesis (many agents, long horizons, a
real outside checker; Plan 26 M5), the same agents with trading on solve no
more checker-scored tasks per model call than with trading off (the solo
baseline, Plan 24's trading switch), across matched runs. A toy-scale tie, such
as Plan 24's 2 agents and 28 decisions, is not a disproof
(`docs/MVP_ROADMAP.md`: "scale and lengthen before judging").

## Non-goals

- Authentication, multi-user hosting, production reliability and scale
  engineering while the investment boundary is local prototype
  (`docs/MVP_ROADMAP.md`).
- A second dashboard or a configuration-panel zoo; a view is added only for a
  concrete operator question.
- Scripting the target behavior and calling it emergence: no assigned roles or
  strategies for agents.
- Live-world scoring (Reddit, GitHub stars) as the judge (Plan 24 non-goals).

## Lineage (AES extension)

Rebuilt from `agent_ecology2` (which itself replaced the archived
`agent_ecology`). AE3 was started as a clean rebuild because AE2 had
accumulated code smell and architecture sprawl; six removals approved by Brian
on 2026-02-20 made that concrete: runtime-adjacent process scaffolding,
compatibility shims, duplicated authority boundaries, dashboard frontend
sprawl, dormant subsystems in the default boot path, and broad backward-config
compatibility. AE3 rebuilds ideas and selected behavior; Project Meta records
no formal supersession edge between AE2 and AE3
([Lineage and Restarts](../LINEAGE_AND_RESTARTS.md)).
