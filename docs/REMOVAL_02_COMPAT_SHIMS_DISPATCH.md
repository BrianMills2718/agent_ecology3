# Removal 02: Legacy Compatibility Shims and One-Off Dispatch Paths

Date: 2026-02-20
Status: `approved` (approved by user on 2026-02-20)

## Decision Draft

Do not carry forward backward-compatibility shims and ad hoc dispatch branches from `agent_ecology2` into the AE3 runtime surface unless they are required by a current AE3 caller.

## Concrete Removals Under Review (from `agent_ecology2`)

1. Config raw-dict compatibility layer:
- `src/config.py` keeps both validated config and raw dict for backward compatibility (`load_config`, `get_config`, `get`) (`agent_ecology2/src/config.py:59`, `agent_ecology2/src/config.py:72`).

2. Checkpoint format migration and legacy aliases:
- v1 -> v2 checkpoint migration (`_migrate_v1_to_v2`) (`agent_ecology2/src/simulation/checkpoint.py:88`).
- legacy `tick` alias persisted in save/load (`agent_ecology2/src/simulation/checkpoint.py:66`, `agent_ecology2/src/simulation/checkpoint.py:149`).
- legacy balance key fallback (`compute` -> `llm_tokens`) (`agent_ecology2/src/simulation/checkpoint.py:129`).

3. Legacy logger mode:
- Single-file legacy logging path (`_setup_legacy_logging`) (`agent_ecology2/src/world/logger.py:265`).

4. Deprecated world API aliases and legacy resource fallback:
- `advance_tick()` retained for compatibility (`agent_ecology2/src/world/world.py:427`).
- `is_agent_frozen()` falls back to stock resource mode if rate-limit layer not present (`agent_ecology2/src/world/world.py:718`).

5. Multi-branch invoke dispatch preserved for old artifact styles:
- `genesis_methods` dispatch branch (`agent_ecology2/src/world/action_executor.py:847`).
- `handle_request` branch (`agent_ecology2/src/world/action_executor.py:851`).
- legacy `run()` fallback branch (`agent_ecology2/src/world/action_executor.py:858`).

6. Deprecated action types kept in narrow waist:
- `configure_context` and `modify_system_prompt` still accepted as deprecated action types (`agent_ecology2/src/world/actions.py:26`, `agent_ecology2/src/world/actions.py:61`).

7. Provider detection heuristic fallback:
- string-matching fallback when model metadata lookup fails (`agent_ecology2/src/simulation/runner.py:35`, `agent_ecology2/src/simulation/runner.py:46`).

## AE3 Direction If Approved

1. Typed config only in runtime code paths (no raw dict compatibility helpers as part of the public path).
2. Single checkpoint schema version for AE3 with explicit migration script outside runtime if needed.
3. Event terminology only (`event_number`), no `tick` alias in persisted runtime schemas.
4. One explicit artifact invoke contract (preferred: `handle_request`) with optional short migration adapter behind a feature flag if truly required.
5. No deprecated action aliases in core parser.
6. No silent provider-guess fallbacks in accounting-sensitive paths.

## Risks

1. Older checkpoints and automation that depend on aliases may stop working without migration.
2. Historical artifact code using `run()` or legacy action names may fail until rewritten.

## Mitigation

1. Provide one explicit migration utility for checkpoints and legacy action payloads.
2. Keep a temporary adapter module outside the core runtime path, disabled by default.
3. Add targeted tests proving strict behavior and clear error messages on unsupported legacy inputs.

## Approval Request

If approved, this removal will be marked accepted in `docs/REMOVAL_SEQUENCE.md`, then we will apply the removal decisions in AE3 code and tests.
