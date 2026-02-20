# Removal 06: Full Backward Config Compatibility Requirement

Date: 2026-02-20
Status: `approved` (approved by user on 2026-02-20)

## Decision Draft

AE3 should use one strict config schema and stop carrying broad backward-compatibility behavior for old keys, legacy aliases, and fallback semantics.

## What Is Removed (from AE3 baseline)

1. Legacy key aliases and migration shims in config/executor:
- `agent_ecology2/src/config_schema.py:837`
- `agent_ecology2/src/config_schema.py:844`
- `agent_ecology2/src/world/executor.py:422`

2. Deprecated legacy cost keys kept only for compatibility:
- `agent_ecology2/src/config_schema.py:181`
- `agent_ecology2/config/config.yaml:37`

3. Legacy per-principal key fallback (`starting_credits` alias):
- `agent_ecology2/src/world/world.py:291`

4. Legacy single-file logging mode fallback:
- `agent_ecology2/src/world/logger.py:198`
- `agent_ecology2/src/world/logger.py:265`
- `agent_ecology2/src/world/world.py:208`

5. Legacy permission compatibility paths:
- `agent_ecology2/src/world/permission_checker.py:47`
- `agent_ecology2/src/world/permission_checker.py:263`
- `agent_ecology2/src/world/permission_checker.py:404`

## What Stays

1. Strict validated typed config loading as the single source of truth.
2. Explicit required keys and explicit defaults in one schema.
3. Contract-driven permission model as the normal path.
4. Per-run structured logging mode (run directory + latest pointer).

## Why

1. Multiple alias/fallback paths increase ambiguity and silent misconfiguration risk.
2. AE3 is a clean rebuild, so carrying historical compatibility debt reduces the value of the rewrite.
3. Strict schema errors are faster to debug than permissive fallback behavior.

## Impact / Risk

1. Older AE2-era config files may fail validation in AE3 until migrated.
2. Workflows relying on legacy fields (`starting_credits`, `allowed_imports`, `logging.output_file`) will need updates.
3. If a contract reference is missing, behavior will be explicit failure rather than silent legacy/freeware fallback.

## Mitigation

1. Provide a migration map from AE2 keys -> AE3 keys with examples.
2. Add a one-time config lint/migrate script for common renames.
3. Keep high-quality validation errors that point to exact replacement keys.

## Next Step

Approved. Next step is implementation against the accepted removal set.
