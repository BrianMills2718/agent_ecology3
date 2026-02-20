# Removal 05: Non-Essential Dormant Subsystems in Core Boot Path

Date: 2026-02-20
Status: `approved` (approved by user on 2026-02-20)

## Decision Draft

For AE3 baseline, keep only the minimal runtime needed for autonomous artifact economy loops. Do not include subsystems that are currently disabled by config or mostly observability/extension concerns.

## What Is Removed (from AE3 core path)

1. External capability runtime from core boot:
- `agent_ecology2/src/world/world.py:241`
- `agent_ecology2/src/world/kernel_interface.py:1048`
- `agent_ecology2/src/world/capabilities.py`

2. Task-based mint subsystem from core action/query surface:
- `agent_ecology2/src/world/world.py:262`
- `agent_ecology2/src/world/action_executor.py:1508`
- `agent_ecology2/src/world/kernel_queries.py:507`
- `agent_ecology2/src/world/mint_tasks.py`

3. Secondary in-memory invocation registry from core runtime:
- `agent_ecology2/src/world/world.py:318`
- `agent_ecology2/src/world/action_executor.py:1856`
- `agent_ecology2/src/world/kernel_queries.py:422`
- `agent_ecology2/src/world/invocation_registry.py`

4. Rich per-agent resource metrics provider as a default boot dependency:
- `agent_ecology2/src/world/world.py:225`
- `agent_ecology2/src/world/world.py:461`
- `agent_ecology2/src/world/resource_metrics.py`

## Why These Are Good Candidates

1. External capabilities are empty by default in current config:
- `agent_ecology2/config/config.yaml:891`

2. Mint tasks are disabled by default in current config:
- `agent_ecology2/config/config.yaml:671`

3. Invocation registry duplicates data already emitted to event logs (`invoke_success`/`invoke_failure`), adding another authority surface.

4. Resource metrics provider is primarily a visibility/reporting layer, not required for core execution semantics.

## What Stays in AE3 Core

1. Contract-governed artifact access and action execution.
2. Ledger + rate tracker + budget accounting integration.
3. Mint auction economics (core resource loop).
4. Minimal state/event API and JSONL observability.

## Impact / Risk

1. Agents lose built-in capability request/use primitives unless enabled via extension.
2. Task-based mint workflows are unavailable in baseline.
3. `query_kernel` invocation-history convenience endpoint is removed unless rebuilt over logs.
4. Rich prompt-facing resource telemetry becomes optional instead of default.

## Mitigation

1. Keep each removed subsystem as an opt-in extension package in AE3 (not booted by default).
2. Keep explicit extension interfaces so these can be reattached without touching core kernel code.
3. Preserve event logs as canonical observability, then derive richer views out-of-path.

## Deferred Extension Candidate

External capabilities are explicitly deferred, not discarded:
1. Revisit only after AE3 core runtime is proven stable in baseline operation.
2. Reintroduce as an extension module with explicit enablement and tests.
3. Keep it out of default boot path until core stability and accounting behavior are validated.

## Next Step

Approved. Next step is implementation against the accepted removal set.
