# Removal 01: Runtime-Adjacent Governance/Process Scaffolding

Date: 2026-02-20
Status: `approved` (approved by user on 2026-02-20)

## Decision

Do not port governance/process scaffolding from `agent_ecology2` into `agent_ecology3` runtime.

## Concrete Exclusions (from `agent_ecology2`)

1. `agent_ecology2/.claude/`
2. `agent_ecology2/meta-process/`
3. `agent_ecology2/meta/` (including acceptance gate artifacts)
4. `agent_ecology2/worktrees/`
5. `agent_ecology2/hooks/`
6. `agent_ecology2/scripts/` (except any future explicit migration utility)
7. `agent_ecology2/.github/` workflow complexity tied to old plan governance

## What Stays in AE3 Instead

1. Runtime kernel code only under `src/agent_ecology3/world`.
2. Simulation runtime only under `src/agent_ecology3/simulation`.
3. Dashboard/runtime observability only under `src/agent_ecology3/dashboard`.
4. Focused tests only under `tests/`.
5. Compact docs under `docs/`.

## Why This Removal

1. These directories add heavy process complexity but do not execute core simulation economics.
2. They create cognitive noise that obscures kernel behavior and debugging.
3. They increase maintenance burden and encourage coupling between runtime and planning process.

## Risks

1. Loss of old operational workflow helpers.
2. Some contributors may miss prior governance automation.

## Mitigation

1. Keep old repository (`agent_ecology2`) intact as historical reference.
2. Re-introduce only narrowly scoped tooling later if runtime need is proven.
3. Document the reduced process model explicitly in AE3 docs.

## Acceptance Criteria

1. AE3 runtime works without importing any excluded path.
2. No runtime module in AE3 references governance/worktree helpers.
3. Core workflows (run simulation, inspect logs, use dashboard) remain intact.
