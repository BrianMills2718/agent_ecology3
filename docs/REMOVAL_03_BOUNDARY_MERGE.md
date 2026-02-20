# Removal 03: Duplicated Abstractions and Authority Boundary Merges

Date: 2026-02-20
Status: `approved` (approved by user on 2026-02-20)

## Decision Draft

Do not port duplicated authority/control surfaces from `agent_ecology2` into AE3. Keep one canonical execution path per concern (resources, invocation, permissions, kernel API), while access rights continue to be governed by contracts.

## Concrete Duplications Under Review (from `agent_ecology2`)

1. Resource control split across multiple modules with overlapping responsibilities:
- `ResourceManager` claims unified handling of balances, quotas, and rate limits (`agent_ecology2/src/world/resource_manager.py:1`, `agent_ecology2/src/world/resource_manager.py:26`, `agent_ecology2/src/world/resource_manager.py:321`).
- `Ledger` also manages balances/resources and wraps `RateTracker` (`agent_ecology2/src/world/ledger.py:195`, `agent_ecology2/src/world/ledger.py:528`).
- `World` adds another quota API wrapper layer on top (`agent_ecology2/src/world/world.py:829`, `agent_ecology2/src/world/world.py:870`).
- `ResourceMetricsProvider` introduces an additional resource view model path (`agent_ecology2/src/world/resource_metrics.py:1`, `agent_ecology2/src/world/resource_metrics.py:71`).

2. Invocation pipeline split across executor/action handler/helper modules:
- `ActionExecutor` owns invoke execution and records invocation registry/events (`agent_ecology2/src/world/action_executor.py:672`, `agent_ecology2/src/world/action_executor.py:1838`).
- `invoke_handler.py` also logs invoke events with a different event naming convention (`invoke` / `invoke_failed`) (`agent_ecology2/src/world/invoke_handler.py:204`, `agent_ecology2/src/world/invoke_handler.py:224`).
- `InvocationRegistry` exists as another parallel observability store (`agent_ecology2/src/world/invocation_registry.py:95`).

3. Kernel API duplication for the same operations:
- `World` exposes convenience methods for artifact read/write and quota actions (`agent_ecology2/src/world/world.py:572`, `agent_ecology2/src/world/world.py:606`, `agent_ecology2/src/world/world.py:829`).
- `KernelInterface` exposes parallel methods that route to `World` or actions (`agent_ecology2/src/world/kernel_interface.py:142`, `agent_ecology2/src/world/kernel_interface.py:428`, `agent_ecology2/src/world/kernel_interface.py:595`).
- `ActionExecutor` independently exposes equivalent action paths (`agent_ecology2/src/world/action_executor.py:163`, `agent_ecology2/src/world/action_executor.py:261`).

4. Query handling duplicated across action path and kernel interface path:
- `ActionExecutor.query_kernel` dispatches through world query handler (`agent_ecology2/src/world/action_executor.py:1078`).
- `KernelState.query` constructs/uses `KernelQueryHandler` again (`agent_ecology2/src/world/kernel_interface.py:250`, `agent_ecology2/src/world/kernel_interface.py:267`).

5. Permission checking authority split:
- `permission_checker.py` contains contract permission core (`agent_ecology2/src/world/permission_checker.py:1`, `agent_ecology2/src/world/permission_checker.py:118`).
- `executor.py` wraps and re-exports permission checks (`agent_ecology2/src/world/executor.py:710`).
- `ActionExecutor` directly calls executor permission checks in many action paths (`agent_ecology2/src/world/action_executor.py:169`, `agent_ecology2/src/world/action_executor.py:597`, `agent_ecology2/src/world/action_executor.py:896`).

6. LLM accounting authority split:
- Local world wrapper `src/world/llm_client.py` computes/estimates cost itself (`agent_ecology2/src/world/llm_client.py:1`, `agent_ecology2/src/world/llm_client.py:53`).
- `executor.create_syscall_llm` invokes that local wrapper and applies budget deductions (`agent_ecology2/src/world/executor.py:110`, `agent_ecology2/src/world/executor.py:189`).
- `SimulationEngine` separately tracks API budget and per-model pricing (`agent_ecology2/src/world/simulation_engine.py:1`, `agent_ecology2/src/world/simulation_engine.py:165`).

## AE3 Direction If Approved

1. Resources: single accounting/control path = `Ledger` + `RateTracker`; remove parallel quota/accounting subsystems in runtime path.
2. Invocation: single execution path = executor/action path; one event schema and one metrics surface.
3. Kernel API: one command path (typed actions) plus a minimal service surface; no overlapping wrappers.
4. Querying: one query handler path, reused by both external and in-sandbox callers.
5. Permissions: single contract engine entrypoint, no scattered `_check_permission` call sites. Contracts remain the source of access rights.
6. LLM accounting: single source of truth = external `llm_client`; world only reconciles budget/rate usage.

## Risks

1. Refactor touches hot paths (invoke, permissions, resource checks) and can cause regressions if done without tests.
2. Existing scripts/tests that assume older event names or wrapper methods may fail.

## Mitigation

1. Lock strict integration tests around invoke, permissions, and budget reconciliation before removing duplicate paths.
2. Keep one temporary adapter layer for renamed APIs/event fields during migration, then delete it in a follow-up removal.
3. Maintain migration notes that map old entrypoints to canonical AE3 entrypoints.

## Approval Request

Approved. Next step is to enforce these authority boundaries in AE3 code and tests.
