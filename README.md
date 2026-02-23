# Agent Ecology 3

Agent Ecology 3 is a clean-room rewrite of `agent_ecology2` focused on:

- Clear kernel boundaries (`World`, `ActionExecutor`, `SafeExecutor`, `SimulationRunner`)
- Explicit resource accounting (scrip, llm_budget, disk quota, rolling rate limits)
- Contract-driven artifact access control
- Autonomous artifact loops (`has_loop=True`)
- JSONL-first observability with a minimal FastAPI dashboard

All six approved removals from AE2 are applied as AE3 design constraints:
- no compat-shim sprawl
- no duplicated authority surfaces
- no dashboard panel zoo
- no dormant subsystems in default boot path
- strict config schema (no backward-key aliasing behavior)

## Quick Start

```bash
cd /home/brian/projects/agent_ecology3
pip install -e .
python run.py --duration 120
# or: agent-ecology3 --duration 120
```

## CLI

```bash
python run.py --config config/config.yaml
python run.py --duration 300 --agents 4
python run.py --duration 300 --agents 4 --llm-loop on
python run.py --duration 300 --agents 4 --model claude-code/opus --llm-loop on
python run.py --duration 300 --agents 4 --loop-llm-cooldown 2.0
python run.py --duration 300 --agents 4 --llm-loop on --loop-llm-cooldown 2.0
python run.py --duration 300 --agents 4 --llm-loop on --loop-forced-explore reduced
python run.py --duration 300 --agents 4 --llm-loop on --loop-forced-explore off
python run.py --dashboard
python run.py --dashboard-only
PYTHONPATH=src python -m agent_ecology3.analysis.emergence_report --events logs/latest/events.jsonl --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.emergence_report --events logs --run-id run_20260220_183640 --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.emergence_report --events logs --run-id run_20260220_183640 --log-experiment --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.emergence_report --list-experiments --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.emergence_report --compare-experiments RUN_A RUN_B --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.emergence_report --analyze-experiments --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix --runs 5 --duration 30 --agents 4 --llm-loop on --loop-llm-cooldown 0 --log-experiment --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix --runs 3 --duration 900 --agents 4 --model claude-code/opus --target-llm-calls 200 --llm-loop on --loop-llm-cooldown 0 --log-experiment --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix --runs 5 --duration 900 --agents 4 --llm-loop on --loop-forced-explore off --target-llm-calls 80 --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix --runs 5 --duration 900 --agents 4 --llm-loop on --target-llm-calls 80 --loop-forced-explore reduced --seed-base 100 --seed-step 1 --min-llm-calls 1 --min-llm-valid-decisions 5 --invalid-run-policy drop --llm-preflight auto --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix --runs 5 --duration 900 --agents 4 --llm-loop on --loop-forced-explore reduced --target-llm-calls 80 --subscription-estimated-cost-multiplier 2.0 --seed-base 100 --seed-step 1 --min-llm-calls 1 --min-llm-valid-decisions 5 --invalid-run-policy drop --llm-preflight auto --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix --runs 5 --duration 900 --agents 4 --llm-loop on --target-llm-calls 80 --loop-forced-explore reduced --experiment-condition-id forced_reduced --experiment-scenario-id phase1_falsification --experiment-phase phase1 --log-experiment --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix --runs 5 --duration 900 --agents 4 --llm-loop on --target-llm-calls 80 --loop-forced-explore reduced --gate-policy '{"pass_if":{"loop_action_entropy_bits_mean_gte":2.1}}' --gate-fail-exit-code --pretty
```

## Autonomous Loop Behavior

- Loop artifacts can call LLM when `llm.enable_bootstrap_loop_llm: true`.
- The parser accepts both canonical AE3 action JSON and common LLM variants (`action` + `parameters`) and normalizes to internal intents.
- Non-canonical `query_kernel` types are inferred to supported kernel queries to reduce invalid-action churn.
- Loop prompt state includes principal-scoped `recent_feedback` (recent action attempts/failures and error codes) from in-memory runtime state to reduce repeated failed moves.
- Each loop invocation emits a `loop_decision` event trace with chosen action, fallback usage, and result status.
- Loop action output is hard-gated to `write_artifact`, `read_artifact`, `transfer`, `transfer_resource`, `submit_to_mint`, and `query_kernel` (invalid actions are rewritten to deterministic fallback).
- Loop normalization auto-prices non-scratch `write_artifact` outputs (`read_price=1` when omitted) to make paid consumption observable in emergence runs.
- Loop read-target selection now prioritizes affordable priced cross-principal artifacts before free artifacts.
- Scarce LLM rights can be contracted via `transfer_resource` (`resource=llm_budget`) between principals.
- Gate and feedback behavior can be toggled with `llm.loop_action_gate_enabled` and `llm.loop_prompt_feedback_enabled`.
- Loop LLM calls can be rate-shaped per principal using `llm.loop_llm_cooldown_seconds` (default `0.0`, disabled) with in-memory per-principal cooldown tracking (control path does not depend on JSONL reads).
- Forced exploration guardrails are tunable via `llm.loop_forced_explore_mode` (`baseline`, `reduced`, `off`) for falsification runs.
- Agent SDK loop-call options can be forwarded from config with `llm.agent_cwd`, `llm.agent_max_turns`, and `llm.agent_permission_mode`.
- Subscription-billed agent models can still deplete `llm_budget` via `llm.subscription_budget_charge_mode` (`estimated` by default) so budget scarcity stays binding even when provider-reported USD marginal cost is zero.
- For `claude-code/*` loop calls, AE3 now injects an MCP stdio `ae3_action` tool bridge so agent-mode tool calls are captured and parsed symmetrically with non-agent tool calls.
- Each principal now boots with cognitive artifacts (`*_strategy`, `*_state`, `*_notebook`) carrying role specialization, objective progress, and a persistent journal.
- Loop prompts consume this memory snapshot (`memory.next_objective`, `memory.objectives`, `memory.stagnation_count`) to reduce one-action collapse and encourage discover->read->produce->trade->mint cycles.

## Experiment Integration

- AE3 emergence analysis integrates with `llm_client` experiment logging (`start_run`, `log_item`, `finish_run`) so run metrics land in the existing experiment registry and SQLite observability DB.
- `emergence_report` can also query that registry via `--list-experiments`, `--detail-experiment`, and `--compare-experiments`.
- `emergence_report` now includes loop-decision metrics from `loop_decision` events: `fallback_rate`, `decision_success_rate`, `repeat_error_rate`, per-principal `loop_decision_trends`, and `loop_action_entropy_bits`.
- `loop_decision` events now carry MECE decision-origin tags (`llm_valid`, `llm_invalid_fallback`, `forced_explore`, `recovery`, `fallback_without_llm`) plus `forced_explore_reason`.
- `emergence_report` now includes policy-distortion, LLM-engagement, and value-weighted metrics: `forced_explore_rate`, `gate_fallback_rate`, `recovery_fallback_rate`, `decision_origin_share`, `llm_call_errors`, `llm_attempt_rate`, `llm_valid_decision_rate`, `cross_paid_consumption_amount`, `reuse_weighted_artifact_value_total`, `specialization_hhi_mean`, and mint downstream value proxies.
- `emergence_report` also reports scarce-resource transfer metrics: `resource_transfers_total`, `llm_budget_transfer_amount`, and `cross_llm_budget_transfer_amount`.
- `scarcity_matrix` runs repeated fixed-config baselines, logs each run to `llm_client`, aggregates mean/std/min/max metrics, and evaluates KPI lock checks in one command.
- `scarcity_matrix` supports matched-condition seeds via `--seed-base` and `--seed-step`, and can gate LLM-engagement validity with `--min-llm-calls`, `--min-llm-valid-decisions`, `--min-llm-attempt-rate`, `--min-llm-valid-decision-rate`, and `--invalid-run-policy`.
- `scarcity_matrix` can run an LLM path preflight (`--llm-preflight auto|on|off`) and fail fast before long runs when the configured model path is unavailable.
- `scarcity_matrix` can override subscription scarcity pressure directly with `--subscription-estimated-cost-multiplier` for calibrated sweeps without creating temporary config files.
- `scarcity_matrix` can tag each logged run with cohort metadata (`--experiment-condition-id`, `--experiment-scenario-id`, `--experiment-phase`) while auto-recording per-run `seed` and `replicate`.
- `scarcity_matrix` can evaluate a matrix-level gate policy (`--gate-policy`) over aggregate signals and optionally fail with exit code `2` (`--gate-fail-exit-code`).
- Gate policy presets are provided at `config/gates/phase1_matrix_gate.json` (strict KPI lock) and `config/gates/phase1_matrix_gate_fast.json` (short-run smoke gate).
- KPI lock entropy now evaluates loop decisions (`loop_action_entropy_bits`) instead of all low-level action events, and exchange pressure passes on scrip flow, llm_budget flow, or sufficient cross-resource transfer events.
- `scarcity_matrix` supports both wall-clock runs and call-budget-normalized runs via `--target-llm-calls`; this reduces model-latency bias in emergence comparisons.
- If `llm_client` is not installed in your active env, set `LLM_CLIENT_REPO=/home/brian/projects/llm_client` (or pass `--llm-client-repo`) so the analyzer can import directly from repo source.

## Project Layout

```text
agent_ecology3/
  run.py
  config/config.yaml
  src/agent_ecology3/
    world/        # kernel primitives, ledger, contracts, executor
    simulation/   # autonomous loop runner
    dashboard/    # minimal API + lightweight status UI
  tests/
```

## Docs

- `docs/REWRITE_SCOPE.md` - keep/add/remove scope for the rebuild.
- `docs/REMOVAL_SEQUENCE.md` - ordered removal plan for review one item at a time.
- `docs/REMOVAL_01_RUNTIME_GOVERNANCE.md` - detailed review doc for removal #1.
- `docs/REMOVAL_02_COMPAT_SHIMS_DISPATCH.md` - detailed review doc for removal #2.
- `docs/REMOVAL_03_BOUNDARY_MERGE.md` - detailed review doc for removal #3.
- `docs/REMOVAL_04_DASHBOARD_SPRAWL.md` - detailed review doc for removal #4.
- `docs/REMOVAL_05_DORMANT_BOOT_SUBSYSTEMS.md` - detailed review doc for removal #5.
- `docs/REMOVAL_06_BACKWARD_CONFIG_COMPAT.md` - detailed review doc for removal #6.
- `docs/IMPLEMENTATION_BASELINE.md` - implemented AE3 baseline scope and validation record.
- `docs/RESOURCE_ACCOUNTING.md` - real vs pseudo accounting decision framework.
- `docs/ACCOUNTING_CONSTANTS.md` - accounting-sensitive numbers/flags with update triggers and source links.
- `docs/CHATGPT_FULL_CONTEXT.md` - full project context handoff for external advisory review.
