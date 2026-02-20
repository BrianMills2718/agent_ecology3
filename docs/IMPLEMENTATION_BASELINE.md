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
