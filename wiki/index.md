---
title: Agent Ecology 3
type: index
authority: derived
updated: 2026-10-06
entry:
  answers: "What Agent Ecology 3 is, whether it is still being worked on, what the current experiment is, how to run or reopen a run, and where its decisions and past results live."
  not_when: "You want the older full-featured runtime (see agent_ecology2) or the shared LLM client itself (see llm_client)."
  aliases: [AE3, agent_ecology3]
  status: active
  as_of: 2026-10-05
  authority: docs/MVP_ROADMAP.md
topics:
  - title: "Roadmap and current status"
    path: "docs/MVP_ROADMAP.md"
    answers: "What is the goal, what is done, and what comes next?"
  - title: "Latest plan (Plan 24)"
    path: "docs/plans/24_external_score_vs_solo.md"
    answers: "How are agents scored by an outside checker, and what did the toy-scale trading-vs-solo comparison show?"
  - title: "Implementation reference"
    path: "docs/IMPLEMENTATION_BASELINE.md"
    answers: "Which module owns what, and how is a run started and reopened?"
  - title: "Model description (ODD) and view coverage"
    path: "docs/model/ODD.md"
    answers: "What exactly the agents, artifacts, tasks, checker and actions are, what each agent sees per turn, which events the kernel logs, and which of them each dashboard view shows."
  - title: "Lineage and standing constraints"
    path: "docs/LINEAGE_AND_RESTARTS.md"
    answers: "Why do three Agent Ecology repositories exist, and which rebuild rules still bind?"
  - title: "Failure-mode dossier"
    path: "docs/FAILURE_MODE_DOSSIER.md"
    answers: "Which failures have already happened across AE1-AE3, and how are they prevented?"
---
# Agent Ecology 3

Agent Ecology 3 (AE3) is Brian's local workbench for running small economies of
LLM agents under scarce resources: agents spend scrip (the in-world currency)
and a limited model budget, buy and sell artifacts (pieces of text they write)
from each other, and earn new scrip from a mint. Each
decision is logged, and a finished run can be reopened read-only in a browser
dashboard. The workbench itself is complete; the project's central bet (that
trading makes the same agents more productive) has not been tested at the
scale it is about.

## State as of 2026-10-05
- Active. Plan 24 (PRs #63-#71) built an outside checker that pays only for
  solved HumanEval tasks, a switch that turns trading off, and a
  trading-vs-solo comparison view in the dashboard.
- At toy scale (2 agents, 28 decisions, 8 tasks) trading gave no gain in three
  matched pairs. Brian judged that setting too small to test a thesis about
  scale and long horizons, so it is not a verdict.
- Current goal: get the system working and the agents behaving intelligently
  so it can scale (Plan 25). Working now: long-lived Codex agents that keep
  memory and act through the kernel's MCP tool (8 agents × 20 turns completed,
  80/80 tasks solved), and a World Substrate living view of each run. Agents also
  test their own code before submitting. Tasks build on each other: in a 16-agent, 40-turn run, passing solutions called another agent's helper 19 times.
- `make check` passes (pytest and mypy), and preserved runs reopen in the
  dashboard from their committed evidence bundles.

## Where to go next
| If you want to... | Read |
|---|---|
| Know the goal, status, and next work | [MVP roadmap](../docs/MVP_ROADMAP.md) |
| See the outside checker and the toy-scale comparison | [Plan 24](../docs/plans/24_external_score_vs_solo.md) |
| Know the exact model rules and which events each view shows | [Model description](../docs/model/ODD.md), [view coverage](../docs/model/VIEW_COVERAGE.md) |
| Run a simulation or reopen a run | [README](../README.md) |
| Find which module owns what | [Implementation reference](../docs/IMPLEMENTATION_BASELINE.md) |
| Understand resource accounting | [Resource accounting](../docs/RESOURCE_ACCOUNTING.md) |
| Know why AE3 exists and which rebuild rules still bind | [Lineage and restarts](../docs/LINEAGE_AND_RESTARTS.md) |
| Avoid a known failure | [Failure-mode dossier](../docs/FAILURE_MODE_DOSSIER.md) |
| Read architecture decisions | [ADR index](../docs/adr/AGENTS.md) |
| Browse plans and their status | [Plan index](../docs/plans/AGENTS.md) |
| Work here as an agent | [AGENTS.md](../AGENTS.md) |

## Open concerns
No GitHub issues are open for this repository's documentation. Known gaps
from the 2026-10-05 sweep are listed in the description of the
`docs-consolidation-2026-10-05` pull request; `ISSUES.md` holds the
repository's own issue register.

## History (on demand)
On 2026-10-05 the February 2026 rewrite-planning records
(`docs/REWRITE_SCOPE.md`, `docs/REMOVAL_SEQUENCE.md`, `docs/REMOVAL_01..06_*.md`),
the ChatGPT context handoff (`docs/CHATGPT_FULL_CONTEXT.md`),
`docs/ACCOUNTING_CONSTANTS.md`, and the vendored process-pattern library
(`docs/meta-patterns/`) were removed. Their binding content moved into the
lineage, accounting, and implementation documents above. Recover any of them
with `git log --all -- <path>` and `git show 28574ed:<path>`. Completed plans
and evaluations stay in `docs/plans/` and `docs/evaluations/` as evidence.

## If this page did not answer your question
Find the answer, then add the route here before finishing the task that made
you look. Link the native authority; do not copy it.
