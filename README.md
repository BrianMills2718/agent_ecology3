# Agent Ecology 3

A local workbench for running small economies of LLM agents under scarce
resources and inspecting what they did. Agents spend scrip (the in-world
currency) and a limited model budget, write artifacts (pieces of text) and sell
them to each other, and earn new scrip from a mint; every
decision is logged and a completed run can be reopened read-only in a browser
dashboard.

AE3 is a clean rebuild of `agent_ecology2`. Why it exists, and the design
constraints it carries from that rebuild, are in
[Lineage and Restarts](docs/LINEAGE_AND_RESTARTS.md).

## Where it stands

The roadmap is the authority for outcome, status, and next work:
[docs/MVP_ROADMAP.md](docs/MVP_ROADMAP.md). In short: the local workbench is
complete (launch, watch, reopen a run), and
[Plan 24](docs/plans/24_external_score_vs_solo.md) added an automatic outside
checker that pays agents for solved benchmark tasks, a switch that turns
trading off, and a trading-vs-solo comparison view. At toy scale (2 agents, 28
decisions) trading gave no gain, which is expected: the project's bet is that
cooperation pays only at scale and over long horizons. The current work
([Plan 25](docs/plans/25_scale_shakeout.md)) is a working, intelligent ecology:
long-lived Codex agents that test their own code, on tasks meant to build on each other's
helpers now run at 16 agents for 40 turns; Plan 25 holds the next action.

## Quick start

Requires [uv](https://docs.astral.sh/uv/). `uv sync` installs the pinned
shared `llm_client` and the dev tools.

```bash
uv sync
uv run python run.py --duration 5     # provider-free: the LLM loop is off by default
uv run python run.py --help           # all simulation flags
make check                            # pytest + mypy, through uv
```

A run writes `logs/<run_id>/events.jsonl` and points `logs/latest` at it.
`--llm-loop on` makes the agents call the configured model (this spends money).

Run long-lived agents (each a resumed Codex session acting only through the
kernel; uses the ChatGPT subscription) on a locally built task bank, and watch
them in the dashboard's Living view:

```bash
uv run python scripts/build_codeflow_bank.py --agents 8 --problems 16 --seed 25101
uv run python scripts/run_resident_ecology.py --agents 8 --turns 20 \
  --task-bank ~/.cache/agent_ecology3/codeflow_bank_a8_p16_s25101.jsonl --keep-serving
```

Reopen a preserved run in the dashboard, read-only and with zero model calls:

```bash
mkdir -p /tmp/ae3-review
tar -xzf docs/evaluations/evidence/run_bundles/plan19_luna_live_economic_mvp_v1.tar.gz -C /tmp/ae3-review
uv run python scripts/run_recoverable_evaluation.py review \
  --data-dir /tmp/ae3-review --host 127.0.0.1 --port 9300
# then open http://127.0.0.1:9300/
```

Launching a new bounded model run also goes through
`scripts/run_recoverable_evaluation.py` (`start`, `serve`, `resume`, ...); the
plan that owns a run gives its exact command and spend limit.

## Documentation

| If you want to... | Read |
|---|---|
| Know the goal, status, and what comes next | [docs/MVP_ROADMAP.md](docs/MVP_ROADMAP.md) |
| See the latest completed plan (outside checker, trading switch) | [docs/plans/24_external_score_vs_solo.md](docs/plans/24_external_score_vs_solo.md) |
| Browse all plans and their status | [docs/plans/AGENTS.md](docs/plans/AGENTS.md) |
| Understand how the code is organized and how runs work | [docs/IMPLEMENTATION_BASELINE.md](docs/IMPLEMENTATION_BASELINE.md) |
| Understand resource accounting and its constants | [docs/RESOURCE_ACCOUNTING.md](docs/RESOURCE_ACCOUNTING.md) |
| Know why AE3 exists and which rebuild constraints still bind | [docs/LINEAGE_AND_RESTARTS.md](docs/LINEAGE_AND_RESTARTS.md) |
| Avoid repeating a known failure | [docs/FAILURE_MODE_DOSSIER.md](docs/FAILURE_MODE_DOSSIER.md) |
| Read architecture decisions | [docs/adr/AGENTS.md](docs/adr/AGENTS.md) |
| Check a past experiment's result and evidence | [docs/evaluations/](docs/evaluations/) (evidence bundles under `evidence/`) |
| Work in this repository as an agent | [AGENTS.md](AGENTS.md) |

Completed plans and evaluations are evidence, not instructions: an evaluation
marked invalid or inconclusive (for example Evaluations 04 and 07) must not be
cited as a behavioral result or rerun under the same number.

## History

Retired documents (the February 2026 rewrite-planning records, the 2026-02
ChatGPT context handoff, the vendored meta-process pattern library, and the
old accounting-constants page) were removed on 2026-10-05; each removal commit
names its successor. Recover any of them with
`git log --all -- <path>` and `git show 28574ed:<path>`.
