# Plan #2: Mint scorer llm_client migration

**Status:** ✅ Complete

**Verified:** 2026-07-10T06:26:36Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-07-10T06:26:36Z
tests:
  unit: 51 passed, 2 warnings in 1.55s
  e2e_smoke: skipped (no e2e directory)
  e2e_real: skipped (--skip-real-e2e)
  doc_coupling: passed
commit: 1cb69ee
```
**Type:** implementation
**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** `src/agent_ecology3/world/mint.py` imports LiteLLM directly, calls `litellm.completion()`, parses JSON manually, computes provider cost from LiteLLM internals, and silently falls back on any exception.

**Target:** Mint scoring goes through shared `llm_client.call_llm_structured()` with explicit `task`, per-call `trace_id`, configurable `max_budget`, schema-validated output, and observable fallback details.

**Why:** Brian's ecosystem policy now requires projects to register LLM work through `llm_client` unless a human-approved exception is recorded. Mint scoring is production runtime code, not a benchmark/provider comparison exception.

---

## References Reviewed

- `src/agent_ecology3/world/mint.py` - current LiteLLM-backed mint scorer and auction resolution path.
- `src/agent_ecology3/config.py` - current LLM and mint configuration boundaries.
- `src/agent_ecology3/world/world.py` - mint scorer construction from config.
- `pyproject.toml` - current dependencies include direct LiteLLM.
- `docs/plans/CLAUDE.md` - project plan/commit convention.
- `llm_client.core.client.call_llm_structured()` - live shared client API returns `(parsed_model, LLMCallResult)`.

---

## Files Affected

- `docs/plans/02_mint_scorer_llm_client.md` (create)
- `docs/plans/CLAUDE.md` (update active plan index)
- `src/agent_ecology3/world/mint.py` (migrate scorer internals)
- `src/agent_ecology3/config.py` (add mint scoring budget config)
- `src/agent_ecology3/world/world.py` (pass scoring budget)
- `config/config.yaml` (document default scoring budget)
- `config/config.tight_scarcity.yaml` (document default scoring budget)
- `tests/test_mint_scorer.py` (create)
- `pyproject.toml` (remove direct LiteLLM dependency)

---

## Plan

### Steps

1. Add a configurable mint scoring `max_budget`.
2. Replace LiteLLM completion and manual JSON parsing with `call_llm_structured()`.
3. Keep `MintScorer.score_artifact()`'s public return type unchanged.
4. Preserve deterministic fallback, but record and surface the LLM failure instead of swallowing it.
5. Remove the direct LiteLLM dependency from project metadata.
6. Add unit coverage for structured success and explicit fallback.
7. Run focused tests and the shared registration-only audit.

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_mint_scorer.py` | `test_mint_scorer_uses_llm_client_structured_output` | Mint scoring calls `llm_client.call_llm_structured()` with task, trace ID, max budget, and returns parsed score/cost. |
| `tests/test_mint_scorer.py` | `test_mint_scorer_fallback_reports_llm_failure` | LLM failures use deterministic fallback without silent `except: pass`. |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `python -m pytest tests/test_mint_scorer.py` | Focused behavior. |
| `python -m pytest tests/test_config_and_actions.py tests/test_runtime_smoke.py` | Config and runtime smoke coverage around world/mint setup. |
| `python -m mypy --follow-imports=skip src/agent_ecology3/world/mint.py tests/test_mint_scorer.py` | Local type check for changed scorer/test modules without pulling existing repo-wide debt into this plan. |
| `python -m llm_client.model_policy_audit --registration-only .` | Confirms no direct provider SDK remains in production code. |

---

## Acceptance Criteria

- [x] Mint scorer has no direct provider SDK import/call.
- [x] Structured scoring uses `task=`, `trace_id=`, and `max_budget=`.
- [x] Scoring budget is configurable via `MintConfig`.
- [x] Fallback is explicit and inspectable.
- [x] Required tests pass.
- [x] Local changed-file type check passes.
- [x] Registration-only audit passes for this repo.

---

## Notes

- `timeout_seconds` remains in `MintScorer` for constructor compatibility, but the migrated call does not pass a provider timeout; `llm_client` owns structured-call timeout policy.
- Per-call trace IDs include a UUID suffix so historical cost in the observability DB does not accidentally trip future mint scoring calls for the same artifact ID.
