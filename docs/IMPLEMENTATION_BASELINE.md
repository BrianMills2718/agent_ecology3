# AE3 Implementation Reference

Verified against the code on 2026-10-05 (base commit `28574ed`).

How AE3 is built today: which module owns what, the two ways a run is
started, and where its evidence lands. What to build next lives in
[the roadmap](MVP_ROADMAP.md); why AE3 is shaped this way lives in
[Lineage and Restarts](LINEAGE_AND_RESTARTS.md#standing-constraints-from-the-rebuild).
The February 2026 baseline log and experiment notes that used to fill this
file are in Git history: `git show 28574ed:docs/IMPLEMENTATION_BASELINE.md`.

## Module map

| Area | Path | Owns |
|---|---|---|
| Config | `src/agent_ecology3/config.py` | One strict Pydantic schema; every model rejects unknown keys |
| Kernel | `src/agent_ecology3/world/world.py` | World state, LLM syscalls and their accounting, bootstrap loop artifacts |
| Actions | `world/actions.py`, `world/action_executor.py` | Typed action parsing and execution; emits `loop_decision` events |
| Access rights | `world/contracts.py` | Contract engine; also enforces the trading on/off switch |
| Resources | `world/ledger.py`, `world/rates.py` | Scrip, `llm_budget`, disk, rolling rate limits ([accounting](RESOURCE_ACCOUNTING.md)) |
| Mint | `world/mint.py` | Auction mint (default) and the Plan 24 `task_bounty` mode scored by an automatic checker |
| Other kernel pieces | `world/artifacts.py`, `world/executor.py`, `world/delegation.py`, `world/queries.py`, `world/logger.py` | Artifact store, executable artifacts, charge delegation, `query_kernel`, JSONL event log |
| Luna decisions | `world/luna_actions.py` | Strict structured decision contract for `codex/gpt-5.6-luna` (`llm.decision_output_mode: luna_structured_v1`) |
| Runner | `src/agent_ecology3/simulation/runner.py` | Autonomous loop orchestration |
| Recovery | `simulation/recovery.py` | Fail-closed attempt custody and checkpoints for bounded runs |
| Dashboard | `src/agent_ecology3/dashboard/server.py` | The one FastAPI operator UI (live runs, read-only review, paused launch) |
| Tool bridge | `src/agent_ecology3/mcp/loop_action_server.py` | `ae3_action` MCP tool for `claude-code/*` loop calls |
| Analysis | `src/agent_ecology3/analysis/` | Emergence metrics, scarcity matrices, and the frozen evaluation runners (04-15) |

## Two ways to run

**Plain simulation** (`run.py`, same as `uv run agent-ecology3`). Uses
`config/config.yaml`, writes `logs/<run_id>/events.jsonl` and points
`logs/latest` at it. The LLM loop is off by default
(`llm.enable_bootstrap_loop_llm: false`), so a default run makes no model calls.
`--llm-loop on` turns it on; `--dashboard` serves the dashboard alongside.

**Bounded recoverable run** (`scripts/run_recoverable_evaluation.py`). This is
the workbench path the roadmap's completed capabilities use: `start` creates a
paused, detached worker under a data directory (normally
`~/.local/state/agent_ecology3/<run_id>/`), `serve` shows it in the dashboard,
`resume`/`pause`/`stop`/`shutdown`/`status` operate it, and `review` reopens
finished runs read-only with zero model calls. The run profile (model, prompt,
mint mode, trading on or off) is selected by `--acknowledgement`; Plan 24's
trading and solo conditions use the task bank in `config/tasks/`. Each run
leaves a `run_receipt.json`; receipts cited by the roadmap are copied into
[`evaluations/evidence/run_bundles/`](evaluations/evidence/run_bundles/README.md).

## Decision paths

- **Legacy loop** (`llm.decision_output_mode: legacy`, the default). The model
  returns action JSON; the parser accepts common variants and normalizes them
  to canonical actions; output is gated to `write_artifact`, `read_artifact`,
  `transfer`, `transfer_resource`, `submit_to_mint`, and `query_kernel`.
  `llm.loop_cognition_mode` is `prescribed` (assigned roles and an objective
  cycle) or `minimal` (no prescriptions). Gates, feedback, cooldown, forced
  exploration, and the prompt template are config keys under `llm.`.
- **Luna structured path** (`luna_structured_v1`). One strict structured
  decision per call, no tools; used by Plans 10-24.
- The bounded worker's evaluation profiles (Evaluations 14-15, Plans 19-24)
  use `fail_closed_no_substitute`: a failed model decision stops the run as
  invalid. The legacy loop's deterministic fallbacks are tagged by origin
  (`llm_invalid_fallback`, `fallback_without_llm`, ...) and never count as
  agent decisions (design principles in [AGENTS.md](../AGENTS.md)).

## Evidence and analysis

- Every loop invocation emits a `loop_decision` event; LLM syscall events keep
  the `llm_client` trace ID.
- `python -m agent_ecology3.analysis.emergence_report --events <events.jsonl>`
  computes emergence metrics and can log them to the `llm_client` experiment
  registry. `scarcity_matrix`, `phase1_suite`, `phase1_compare`, and
  `matrix_progress` are the February 2026 matrix tools; they still run but no
  current plan uses them. The `behavioral_*`, `provider_qualification`,
  `hard_call_cap`, `luna_recovery_gate`, and `scarcity_calibration` modules
  belong to frozen evaluations and are documented there.
