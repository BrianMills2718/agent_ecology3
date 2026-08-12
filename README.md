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
python run.py --duration 300 --agents 4 --llm-loop on --loop-prompt-template config/prompts/loop_prompt_variant.txt
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
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix --runs 3 --duration 600 --agents 4 --llm-loop on --target-llm-calls 60 --loop-prompt-template config/prompts/loop_prompt_variant.txt --experiment-condition-id prompt_v1 --log-experiment --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix --runs 5 --duration 900 --agents 4 --llm-loop on --loop-forced-explore reduced --target-llm-calls 80 --subscription-estimated-cost-multiplier 2.0 --seed-base 100 --seed-step 1 --min-llm-calls 1 --min-llm-valid-decisions 5 --invalid-run-policy drop --llm-preflight auto --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix --runs 5 --duration 900 --agents 4 --llm-loop on --target-llm-calls 80 --loop-forced-explore reduced --experiment-condition-id forced_reduced --experiment-scenario-id phase1_falsification --experiment-phase phase1 --log-experiment --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix --config config/config.prescription_ablation.yaml --runs 3 --duration 900 --agents 4 --llm-loop on --loop-cognition-mode minimal --loop-prompt-template config/prompts/loop_prompt_minimal.txt --target-llm-calls 16 --seed-base 12100 --seed-step 1 --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix --runs 5 --duration 900 --agents 4 --llm-loop on --target-llm-calls 80 --loop-forced-explore reduced --gate-policy '{"pass_if":{"loop_action_entropy_bits_mean_gte":2.1}}' --gate-fail-exit-code --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.phase1_suite --runs 3 --duration 600 --target-llm-calls 60 --experiment-scenario-id phase1_suite_demo --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.phase1_suite --conditions reduced,off --runs 10 --duration 420 --target-llm-calls 16 --loop-prompt-template config/prompts/loop_prompt_variant.txt --experiment-scenario-id phase1_confirmatory_demo --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.matrix_progress --jsonl logs/phase1_suite_<scenario>_<condition>_<stamp>.jsonl --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.phase1_compare --baseline-suite logs/phase1_suite_phase1_opus_default_med_20260223_suite.json --candidate-suite logs/phase1_suite_phase1_opus_prompt_variant_med_20260223_suite.json --pretty
PYTHONPATH=src python -m agent_ecology3.analysis.behavioral_comparison --preflight
PYTHONPATH=src python -m agent_ecology3.analysis.behavioral_comparison --reproduce docs/evaluations/evidence/07_behavioral_comparison
```

Evaluation 07's paid `--run-live` mode is intentionally omitted from the quick
examples. It requires separate human authorization, a clean revision retained
by `origin`, and exact acknowledgement of the frozen USD 1.68 maximum.

## Autonomous Loop Behavior

- Loop artifacts can call LLM when `llm.enable_bootstrap_loop_llm: true`.
- Bootstrap loops await `llm_client.acall_llm`; shared-world loop invocations
  remain serialized, the duration monitor stays responsive during provider
  waits, and an in-flight invocation is drained before `SimulationRunner.run()`
  returns. Legacy synchronous artifacts are executed off the event-loop thread.
- The parser accepts both canonical AE3 action JSON and common LLM variants (`action` + `parameters`) and normalizes to internal intents.
- Non-canonical `query_kernel` types are inferred to supported kernel queries to reduce invalid-action churn.
- Loop prompt state includes principal-scoped `recent_feedback` (recent action attempts/failures and error codes) from in-memory runtime state to reduce repeated failed moves.
- Each loop invocation emits a `loop_decision` event trace with chosen action, fallback usage, and result status.
- Loop action output is hard-gated to `write_artifact`, `read_artifact`, `transfer`, `transfer_resource`, `submit_to_mint`, and `query_kernel` (invalid actions are rewritten to deterministic fallback).
- In the default `prescribed` cognition mode, loop normalization auto-prices non-scratch `write_artifact` outputs (`read_price=1` when omitted) to make paid consumption observable in emergence runs. The `minimal` ablation mode does not.
- Loop read-target selection now prioritizes affordable priced cross-principal artifacts before free artifacts.
- Scarce LLM rights can be contracted via `transfer_resource` (`resource=llm_budget`) between principals.
- Gate and feedback behavior can be toggled with `llm.loop_action_gate_enabled` and `llm.loop_prompt_feedback_enabled`.
- Loop LLM calls can be rate-shaped per principal using `llm.loop_llm_cooldown_seconds` (default `0.0`, disabled) with in-memory per-principal cooldown tracking (control path does not depend on JSONL reads).
- Forced exploration guardrails are tunable via `llm.loop_forced_explore_mode` (`baseline`, `reduced`, `off`) for falsification runs (default is now `off`).
- Loop prompt text is overrideable via `llm.loop_prompt_template_path` (or CLI `--loop-prompt-template`) so prompt variants can be tested without code edits.
- Agent SDK loop-call options can be forwarded from config with `llm.agent_cwd`, `llm.agent_max_turns`, and `llm.agent_permission_mode`.
- Subscription-billed agent models can still deplete `llm_budget` via `llm.subscription_budget_charge_mode` (`estimated` by default) so budget scarcity stays binding even when provider-reported USD marginal cost is zero.
- For `claude-code/*` loop calls, AE3 now injects an MCP stdio `ae3_action` tool bridge so agent-mode tool calls are captured and parsed symmetrically with non-agent tool calls.
- Agent-SDK syscalls now pass `max_retries=0` explicitly for `claude-code/*`, `codex/*`, and `openai-agents/*` models, matching side-effect-safe no-retry semantics while avoiding repeated retry-disabled warning spam.
- Each principal boots with persistent cognitive artifacts (`*_strategy`, `*_state`, `*_notebook`). `llm.loop_cognition_mode=prescribed` retains assigned roles and the discover->read->produce->trade->mint objective cycle; `minimal` removes those prescriptions while retaining outcome history and resource state.
- LLM syscall and loop-decision events retain the deterministic `llm_client` trace ID. `llm.provider_max_budget_usd`, `llm.provider_budget_reservation_usd`, `llm.num_retries`, and `llm.max_output_tokens` provide bounded evaluation controls without changing the default unlimited provider budget.

## Experiment Integration

- AE3 emergence analysis integrates with `llm_client` experiment logging (`start_run`, `log_item`, `finish_run`) so run metrics land in the existing experiment registry and SQLite observability DB.
- `emergence_report` can also query that registry via `--list-experiments`, `--detail-experiment`, and `--compare-experiments`.
- `emergence_report` now includes loop-decision metrics from `loop_decision` events: `fallback_rate`, `decision_success_rate`, `repeat_error_rate`, per-principal `loop_decision_trends`, and `loop_action_entropy_bits`.
- `loop_decision` events now carry MECE decision-origin tags (`llm_valid`, `llm_invalid_fallback`, `forced_explore`, `recovery`, `fallback_without_llm`) plus `forced_explore_reason`.
- `emergence_report` now includes policy-distortion, LLM-engagement, and value-weighted metrics: `forced_explore_rate`, `gate_fallback_rate`, `recovery_fallback_rate`, `decision_origin_share`, `llm_call_errors`, `llm_attempt_rate`, `llm_valid_decision_rate`, `cross_paid_consumption_amount`, `llm_valid_downstream_value`, `reuse_weighted_artifact_value_total`, `specialization_hhi_mean`, and mint downstream value proxies.
- `emergence_report` also reports scarce-resource transfer metrics: `resource_transfers_total`, `llm_budget_transfer_amount`, and `cross_llm_budget_transfer_amount`.
- `scarcity_matrix` runs repeated fixed-config baselines, logs each run to `llm_client`, aggregates mean/std/min/max metrics, and evaluates KPI lock checks in one command.
- `scarcity_matrix` supports matched-condition seeds via `--seed-base` and `--seed-step`, and can gate LLM-engagement validity with `--min-llm-calls`, `--min-llm-valid-decisions`, `--min-llm-attempt-rate`, `--min-llm-valid-decision-rate`, and `--invalid-run-policy`.
- `scarcity_matrix` can run an LLM path preflight (`--llm-preflight auto|on|off`) and fail fast before long runs when the configured model path is unavailable.
- `scarcity_matrix` can override subscription scarcity pressure directly with `--subscription-estimated-cost-multiplier` for calibrated sweeps without creating temporary config files.
- `scarcity_matrix` can tag each logged run with cohort metadata (`--experiment-condition-id`, `--experiment-scenario-id`, `--experiment-phase`) while auto-recording per-run `seed` and `replicate`.
- `scarcity_matrix` can evaluate a matrix-level gate policy (`--gate-policy`) over aggregate signals and optionally fail with exit code `2` (`--gate-fail-exit-code`).
- `scarcity_matrix` now flushes per-run JSONL and `run_ids.txt` writes immediately and emits compact per-run completion lines, so long runs can be monitored live.
- Evaluation 04 stopped as preregistered and is **inconclusive**: two paid runs failed the frozen validity rule, the minimal condition was not started, and the trace audit found that shared-client tool-call records omitted raw tool-call envelopes. Do not cite its prescribed-condition activity as evidence that behavior survives the minimal ablation.
- Evaluation 05 completed its one allowed 32-call provider/tool assay, but its
  frozen verdict is **not qualified** because the classifier expected a
  persistence-policy key that the public readback API did not expose. A
  diagnostic audit found exact retained payloads and descriptively usable
  actions in 16/16 prescribed and 15/16 minimal calls; that audit does not
  overwrite the frozen verdict, authorize a rerun, or authorize behavioral
  comparison.
- Evaluation 06 passed and received independent adversarial signoff for the
  narrow instrument claim: 16/16 prescribed and 15/16 minimal actions were
  usable, with zero timeout, truncation, trace, or custody failures. It unblocks
  design/preregistration of a fresh behavioral comparison; it does not itself
  establish emergence or a prescription effect.
- Evaluation 07 now preregisters that behavioral comparison as a 12-pair
  exploratory pilot with two ordered reserve pairs, attempt-based stopping,
  observed scarcity checks, and a USD 1.68 hard ceiling. Its one-shot runner,
  zero-provider preflight, full-custody verifier, and saved-evidence reproducer
  are implemented. The evaluation has not been run, and implementation does
  not authorize provider spend.
- `phase1_suite` runs baseline/reduced/off matrix conditions in sequence and writes a scenario-level cohort comparison from `llm_client.compare_cohorts`.
- `phase1_suite` launches matrix children with unbuffered Python (`-u`) so condition driver logs stream progress in real time.
- `matrix_progress` summarizes in-flight matrix JSONL files (completed replicate count, rolling aggregate metrics, last-run key signals) during long-running suites.
- `phase1_compare` compares two suite outputs and reports aggregate plus matched-seed deltas, with a strengths/risks/uncertainties summary.
- `llm_client` is the primary AE3 experiment backbone (registry, cohort comparison, gate evaluation). `prompt_eval` is currently optional for AE3 and only becomes first-class once we add an external-runner bridge that maps `(scenario, condition, seed, replicate)` simulation trials into prompt-eval trial semantics.
- Gate policy presets are provided at:
  - `config/gates/phase1_matrix_gate.json` (strict KPI lock)
  - `config/gates/phase1_matrix_gate_fast.json` (short-run smoke gate)
  - `config/gates/phase1_matrix_gate_value.json` (value-weighted emergence gate)
- KPI lock entropy now evaluates loop decisions (`loop_action_entropy_bits`) instead of all low-level action events, and exchange pressure passes on scrip flow, llm_budget flow, or sufficient cross-resource transfer events.
- `scarcity_matrix` supports both wall-clock runs and call-budget-normalized runs via `--target-llm-calls`; this reduces model-latency bias in emergence comparisons.
- If `llm_client` is not installed in your active env, set `LLM_CLIENT_REPO=/home/brian/projects/llm_client` (or pass `--llm-client-repo`) so the analyzer can import directly from repo source.

## Recommended Profiles (2026-02-23)

Evidence base:

1. Medium matched-seed prompt suite: `runs=5`, seeds `8100..8104`.
2. Confirmatory prompt suite: `phase1_opus_prompt_confirmatory_20260222_215026`, `runs=10` each for `reduced` and `off`, seeds `9100..9109`.

Locked profile recommendation:

1. Primary emergence diagnosis profile:
- `loop-prompt-template=config/prompts/loop_prompt_variant.txt`
- `loop-forced-explore=off`
- Confirmatory mean signals (`n=10`): `forced_explore_rate=0.0`, `llm_valid_decision_rate=0.95395`, `cross_paid_consumption_amount=3.6`, `reuse_weighted_artifact_value_total=7.839976`.

2. Secondary stress profile:
- Same prompt variant + `loop-forced-explore=reduced`
- Confirmatory mean signals (`n=10`): `forced_explore_rate=0.09803`, `llm_valid_decision_rate=0.87697`, `cross_paid_consumption_amount=2.6`, `reuse_weighted_artifact_value_total=5.522996`.
- Use this profile when you explicitly want higher transfer-pressure/churn (`cross_transfer_amount=7.8`) at the cost of more policy injection and lower value-weighted outcomes.

Open uncertainties to keep explicit:

- Off-mode may be shifting behavior from direct transfers to priced artifact consumption (high value, lower transfer counts).
- Mint remains weak relative to transfer/consumption channels and is not yet a reliable emergence axis.
- Keep validating with occasional matched-seed refreshes when prompts/models/config change materially.

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

- `docs/LINEAGE_AND_RESTARTS.md` - canonical comparison of AE1, AE2, and AE3; restart evidence, recurring failure modes, and the unresolved lifecycle decision.
- `docs/evaluations/04_prescription_ablation.md` - preregistered matched-control test and its inconclusive result, provider/runtime failure analysis, evidence bundle, and rerun prerequisites.
- `docs/evaluations/05_provider_tool_qualification.md` - async/provider/tool
  qualification design, one-shot result, classifier failure mode, and immutable
  evidence bundle.
- `docs/evaluations/06_public_readback_qualification.md` - held-out provider
  qualification with a real zero-spend public-readback gate.
- `docs/evaluations/07_behavioral_comparison.md` - frozen paired behavioral
  design, execution controls, validity rules, readout, and authority boundary.
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
