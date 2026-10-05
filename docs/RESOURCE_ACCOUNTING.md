# Resource Accounting

Decided: 2026-02-23. Constants last verified against code: 2026-10-05.

This is the one reference for how AE3 charges scarce resources and which
numbers drive that charge. It absorbed the former `ACCOUNTING_CONSTANTS.md`
(recover with `git show 28574ed:docs/ACCOUNTING_CONSTANTS.md`).

## Decision: hybrid, measured first

AE3 measures real usage where it is cheap and reliable, and uses explicit,
calibrated estimates only where exact accounting is unavailable. Full real
accounting everywhere cost more integration work than its value; full
estimates everywhere were easier to game and drifted from real economics.

| Resource | Charged from |
|---|---|
| LLM calls | Real call count |
| LLM tokens | Provider-reported tokens; `chars / 4` estimate when absent |
| `llm_budget` | Real billed marginal cost; in subscription-included billing, an estimated charge so scarcity still binds |
| CPU | Measured process CPU seconds |
| Disk | Real UTF-8 byte counts |

Guardrails: keep both `estimated_*` and `actual_*` values when available,
make every fallback formula explicit, and never mix units under one metric
name.

## How one LLM syscall is charged

`World._prepare_llm_syscall` reserves an estimated budget and token amount
before the call; `_settle_llm_syscall` reconciles it against measured usage
and cost afterwards; `_fail_llm_syscall` releases the reservation on failure
(all in `src/agent_ecology3/world/world.py`). The synchronous and async
syscall routes share these functions, so their accounting cannot fork.
Agent-SDK models (`claude-code/*`, `codex/*`, `openai-agents/*`) are called
with `max_retries=0` so a side-effecting call is never silently repeated.

`cost` and `marginal_cost` are distinct: `cost` is the attributed cost of the
call, `marginal_cost` the incremental spend (a cache hit is `0`). In
subscription-included billing the provider may report zero USD while
`llm_budget` still depletes through `llm.subscription_budget_charge_mode`.

## Constants

| Name | Value | Location | Change it when |
|---|---:|---|---|
| Token preflight estimate | `max(20, chars // 4)` | `world.py` `_estimate_tokens` | Logged `actual_tokens` show systematic estimation error |
| Cost preflight estimate | `max(0.0002, est_tokens / 1000 * 0.003)` | `world.py` `_prepare_llm_syscall` | Reservations routinely differ a lot from settled cost |
| `llm.subscription_budget_charge_mode` | `estimated` (`actual`, `estimated`, `none`) | `config/config.yaml`, `src/agent_ecology3/config.py` | Subscription-mode runs become unconstrained or starved |
| `llm.subscription_estimated_cost_multiplier` | `1.0` | same | Scarcity is too weak or too strong for the experiment |
| `resources.rate_limits.llm_calls_per_window` | `120` | same | Throughput tuning or provider rate limits change |
| `resources.rate_limits.llm_tokens_per_window` | `200000` | same | Model context or profile changes |
| `resources.rate_limits.cpu_seconds_per_window` | `12.0` | same | Runtime load profile changes |
| `LLM_CLIENT_AGENT_BILLING_MODE` default | `subscription` | `llm_client` `sdk/agents.py` (pinned revision in `pyproject.toml`) | Agent-SDK workflows move to API-key metering |
| `FALLBACK_COST_FLOOR_USD_PER_TOKEN` | `0.000001` | `llm_client` `utils/cost_utils.py` | Fallback estimates prove too high or low in reconciliation |

The experiment configs beside `config/config.yaml` (for example
`config/config.luna_recovery_gate.yaml`) can override the config-backed values;
read the config a run was started with, not only the defaults above.
