# AE3 Baseline Implementation

Date: 2026-02-20

This documents the first runnable AE3 baseline after approving removals #1-#6.

## Implemented Core

1. Strict config loading with unknown-key rejection:
- `src/agent_ecology3/config.py`

2. Kernel runtime and action execution:
- `src/agent_ecology3/world/world.py`
- `src/agent_ecology3/world/action_executor.py`
- `src/agent_ecology3/world/actions.py`
- `src/agent_ecology3/world/contracts.py`
- `src/agent_ecology3/world/ledger.py`
- `src/agent_ecology3/world/rates.py`
- `src/agent_ecology3/world/mint.py`

3. Autonomous loop runner:
- `src/agent_ecology3/simulation/runner.py`

4. Minimal dashboard/API (no panel sprawl):
- `src/agent_ecology3/dashboard/server.py`

5. CLI/runtime entrypoints:
- `run.py`
- `src/agent_ecology3/cli.py`
- `src/agent_ecology3/__main__.py`

## Removed from Default Core Path

1. Task-based mint runtime wiring (`submit_to_task`, mint task queries).
2. Deprecated action aliases (`configure_context`, `modify_system_prompt`).
3. In-memory invocation registry query surface (events are canonical).
4. Legacy config compatibility aliases/extra keys.

## Deferred Extensions

1. External capabilities subsystem (explicitly deferred until core stability is proven).
2. Any non-essential optional systems approved in removal #5.

## Validation

1. Test suite:
- `tests/test_config_and_actions.py`
- `tests/test_runtime_smoke.py`

2. Commands used:
- `pytest -q`
- `python run.py --duration 1 --agents 1`
- `python run.py --dashboard --duration 1 --agents 1`

## Post-Baseline Hardening (2026-02-20)

After initial baseline validation, autonomous loop behavior was hardened to avoid noop collapse and improve interoperability with model-generated action JSON:

1. Action parser normalization:
- `src/agent_ecology3/world/actions.py`
- Normalizes `action`/`parameters` payload shape to canonical AE3 action fields.
- Infers supported `query_kernel` `query_type` values for non-canonical model outputs.
- Coerces numeric strings for economic fields (`amount`, `bid`) where safe.

2. Loop policy hardening:
- `src/agent_ecology3/world/world.py`
- Bootstrap loop prompt now enforces structured single-action JSON without noop.
- Includes state snapshot in prompt context.
- Adds deterministic fallback exploration actions (write/read/transfer/submit_to_mint).

3. Intent logging completeness:
- `src/agent_ecology3/world/actions.py`
- Added missing `to_dict()` implementations for intent classes so logs capture transfer/mint metadata.

4. Additional parser coverage:
- `tests/test_config_and_actions.py`
- Added tests for alias normalization, query-type inference, numeric coercion, and non-object rejection.

5. Emergence verification runs:
- `logs/run_20260220_165346/events.jsonl` (pre-fix reference; noop-only pattern)
- `logs/run_20260220_183640/events.jsonl` (post-fix; mixed actions, cross-agent transfers/reads, mint submissions, and diverging balances)

6. Experiment-infra integration:
- `src/agent_ecology3/analysis/emergence_report.py`
- AE3 summaries can now be logged into `llm_client`'s centralized experiment registry.
- The same command surface supports list/detail/compare over historical AE3 runs via llm_client tables.

7. Additional loop stability hardening:
- `src/agent_ecology3/world/world.py`
- Loop artifacts are `kernel_protected` to prevent accidental overwrite of executable loop code.
- Fallback action selection validates artifact existence via `kernel_state` to reduce not-found churn.
- Read target selection skips principal artifacts to avoid avoidable permission failures.

8. Legacy-informed loop policy signal + traceability:
- `src/agent_ecology3/world/world.py`
- Loop state snapshot now includes compact principal-scoped `recent_feedback` (attempt/failure/error-code/action-type summary) for better next-action selection.
- Prompt instructions explicitly steer away from repeating recently failing action patterns.
- Loop runtime now hard-gates generated actions to the approved loop-safe set and rewrites disallowed outputs to deterministic fallback with explicit gate reason metadata.
- Loop LLM calls now include principal-scoped cooldown gating (`llm.loop_llm_cooldown_seconds`) backed by in-memory per-principal state (not event-log scans in the loop hot path), so loops can continue deterministic actions between LLM decisions.
- `src/agent_ecology3/world/action_executor.py`
- Added dedicated `loop_decision` event with decision payload, fallback metadata, and resulting action status.
- `tests/test_runtime_smoke.py`
- Added runtime coverage for `loop_decision` presence and loop prompt feedback wiring.

## Legacy AE Review Notes (2026-02-20)

Original `archive/agent_ecology` was reviewed for prompt/policy behaviors worth carrying forward into AE3 without restoring old architecture.

1. Richer local observation in loop prompts:
- Source pattern: `archive/agent_ecology/llm_agent_policy.py` (`AgentObservation.to_prompt`).
- Candidate AE3 addition: include compact recent-success/recent-failure summaries (not full event dumps) in loop prompt context.

2. Tighter action contract before execution:
- Source pattern: `archive/agent_ecology/llm_agent_policy.py` (`LLMAction` constrained schema).
- Candidate AE3 addition: keep parser normalization, but add stricter pre-exec action gating so malformed/unsafe actions are corrected earlier.

3. Deterministic fallback with explicit cause:
- Source pattern: `archive/agent_ecology/llm_agent_policy.py` (`_fallback_decision`).
- Candidate AE3 addition: preserve deterministic exploration fallback, but annotate fallback cause in a dedicated decision record.

4. Dedicated policy decision trace:
- Source pattern: `archive/agent_ecology/llm_agent_policy.py` (`LLMAgentState.record_decision`).
- Candidate AE3 addition: add a compact decision-trace event (decision payload, normalization path, fallback trigger) to improve emergence analysis.

5. Keep AE3 strengths while porting signal:
- Keep: contract-governed access, kernel-protected loop artifacts, and `llm_client`-anchored accounting in syscall path.
- Do not reintroduce: old split world/policy runtime or parallel accounting paths.

## Loop Ablation Matrix (2026-02-21)

Matrix design (5 runs each, 8s duration, 3 principals):

1. `no_llm_loop`:
- `llm.enable_bootstrap_loop_llm=false`

2. `llm_no_feedback_no_gate`:
- `llm.enable_bootstrap_loop_llm=true`
- `llm.loop_prompt_feedback_enabled=false`
- `llm.loop_action_gate_enabled=false`

3. `llm_feedback_plus_gate`:
- `llm.enable_bootstrap_loop_llm=true`
- `llm.loop_prompt_feedback_enabled=true`
- `llm.loop_action_gate_enabled=true`

Aggregate means:

1. `no_llm_loop`:
- `actions_total`: 1489.6
- `action_entropy_bits`: 1.8794
- `cross_read_events`: 554.6
- `cross_transfer_amount`: 112.8
- `mint_submissions`: 115.2
- `llm_calls`: 0.0

2. `llm_no_feedback_no_gate`:
- `actions_total`: 27.6
- `action_entropy_bits`: 1.7408
- `cross_read_events`: 2.4
- `cross_transfer_amount`: 0.2
- `mint_submissions`: 0.6
- `llm_calls`: 12.6

3. `llm_feedback_plus_gate`:
- `actions_total`: 28.2
- `action_entropy_bits`: 1.8006
- `cross_read_events`: 2.8
- `cross_transfer_amount`: 0.2
- `mint_submissions`: 0.0
- `llm_calls`: 12.8

Notes:

1. LLM-enabled loop throughput is far lower than deterministic fallback loops at this duration/latency profile.
2. Feedback+gate improved entropy slightly over no-feedback/no-gate in this run set.
3. All runs reported zero action failures; therefore `fallback_rate` and `repeat_error_rate` remained `0.0`.

## Throughput Profiling and Cooldown Optimization (2026-02-21)

Latency profiling from long matrix (`logs/ablation_long_matrix_resume_summary.json`) showed network-bound LLM calls as the throughput bottleneck:

1. `no_llm_loop`:
- `actions_per_sec` mean: `185.48`
- `invoke_run_latency_mean_ms`: `0.2794`

2. `llm_no_feedback_no_gate`:
- `actions_per_sec` mean: `3.1133`
- `llm_latency_mean_ms` mean: `820.4172`
- `invoke_run_latency_mean_ms`: `411.4324`

3. `llm_feedback_plus_gate`:
- `actions_per_sec` mean: `2.62`
- `llm_latency_mean_ms` mean: `1355.829`
- `invoke_run_latency_mean_ms`: `729.051`

Follow-up cooldown benchmark:

1. `cooldown_0` (`llm.loop_llm_cooldown_seconds=0`), `logs/cooldown_benchmark_1771640251.json`:
- `actions_per_sec`: `2.9555`
- `llm_calls_per_sec`: `1.2667`
- `invoke_run_latency_mean_ms`: `408.3693`

2. `cooldown_1` (`llm.loop_llm_cooldown_seconds=1`), `logs/cooldown_benchmark_1771640251.json`:
- `actions_per_sec`: `3.7556`
- `llm_calls_per_sec`: `1.4`
- `invoke_run_latency_mean_ms`: `342.521`

3. `cooldown_3` (`llm.loop_llm_cooldown_seconds=3`), `logs/cooldown_benchmark_3s_1771640376.json`:
- `actions_per_sec`: `20.9`
- `llm_calls_per_sec`: `1.2333`
- `invoke_run_latency_mean_ms`: `78.0245`
- `decision_success_rate`: `1.0`

Decision:

1. Set default `llm.loop_llm_cooldown_seconds` to `3.0` in AE3 baseline.
2. Keep `loop_action_gate_enabled` and `loop_prompt_feedback_enabled` enabled by default.
