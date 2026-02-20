# Accounting Constants and Update Registry

Date: 2026-02-20

This file tracks numeric/accounting knobs that may need future updates.

## Review cadence

1. Subscription/plan assumptions: review monthly.
2. Pricing-related fallback constants: review monthly.
3. Internal operational defaults (rate limits, quotas): review per release or after load-test changes.

## Constants and Flags

| Name | Current value | Location | Purpose | Update trigger | Source(s) |
|---|---:|---|---|---|---|
| `LLM_CLIENT_AGENT_BILLING_MODE` (default) | `subscription` | `llm_client/llm_client/agents.py` | Treat `claude-code`/`codex` as subscription-included (no API USD per call by default). | If billing model changes or you switch to explicit API-key metering for agent SDK workflows. | https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan, https://docs.anthropic.com/en/docs/claude-code/overview, https://ccusage.com/guide |
| `FALLBACK_COST_FLOOR_USD_PER_TOKEN` | `0.000001` | `llm_client/llm_client/client.py` | Emergency fallback when provider cost computation is unavailable. | If fallback estimates prove too high/low in reconciliation. | Internal safeguard; calibrate against provider pricing pages and observed reconciliation deltas. |
| AE3 token preflight heuristic | `chars / 4` | `agent_ecology3/src/agent_ecology3/world/world.py` (`_estimate_tokens`) | Fast preflight estimate before real usage returns. | If systematic token estimation error exceeds acceptable threshold. | Heuristic baseline; calibrate from observed `actual_tokens` in logs. |
| AE3 cost preflight heuristic | `max(0.0002, est_tokens/1000 * 0.003)` | `agent_ecology3/src/agent_ecology3/world/world.py` (`call_llm_as_syscall`) | Budget reservation before settlement to actual marginal cost. | If reservation mismatch is routinely large. | Internal conservative default; calibrate from measured marginal cost distribution. |
| AE3 rate limit defaults: `llm_calls_per_window` | `120` | `agent_ecology3/config/config.yaml` | Rolling call throttle. | Throughput tuning or provider rate-limit changes. | Internal operational default. |
| AE3 rate limit defaults: `llm_tokens_per_window` | `200000` | `agent_ecology3/config/config.yaml` | Rolling token throttle. | Throughput tuning or model-context/profile changes. | Internal operational default. |
| AE3 rate limit defaults: `cpu_seconds_per_window` | `12.0` | `agent_ecology3/config/config.yaml` | Rolling CPU throttle for executable artifacts. | Runtime load profile changes. | Internal operational default. |

## External Subscription Usage References (Not Enforced In Code)

Last checked: 2026-02-20

These values are for operator awareness and alerting calibration only.

| Reference metric | Current reference value | Purpose | Update trigger | Source(s) |
|---|---:|---|---|---|
| Codex Plus local usage window | `~30-150 messages / 5 hours` | Helps calibrate soft warning thresholds for subscription-driven workflows. | If OpenAI plan guidance changes. | https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan |
| Codex Plus cloud usage window | `~5-40 tasks / 5 hours` | Same as above; cloud delegation has a different envelope than local pairing. | If OpenAI plan guidance changes. | https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan |
| Codex Pro local usage window | `~300-1,500 messages / 5 hours` | Optional calibration point if upgrading plan tier. | If OpenAI plan guidance changes. | https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan |
| Codex Pro cloud usage window | `~50-400 tasks / 5 hours` | Optional calibration point if upgrading plan tier. | If OpenAI plan guidance changes. | https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan |
| ccusage block window | `5 hours` | Align local monitoring/alerts with Claude Code reporting windows. | If ccusage changes block semantics. | https://ccusage.com/guide/blocks-reports |
| Claude Code local log retention default | `30 days` | Retention reminder for historical accounting fidelity. | If Claude/ccusage retention defaults change. | https://ccusage.com/guide/monthly-reports |

## Notes

1. `cost` and `marginal_cost` are intentionally distinct:
- `cost` = attributed/original cost context.
- `marginal_cost` = incremental spend impact for this call (cache hits should be `0`).

2. For agent SDK subscription mode, USD cost is intentionally not inferred from token usage by default.
