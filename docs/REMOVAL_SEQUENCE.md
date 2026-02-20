# Removal Sequence (Agent Ecology 2 -> 3)

Date: 2026-02-20

We will evaluate removals in this exact order so each step is clear and reversible.

## 1. Remove runtime-adjacent governance/process scaffolding

Scope:
- Plan/worktree/governance scripts and coordination logic not required for kernel execution.

Why:
- High noise-to-value ratio in runtime code review and maintenance.

Risk:
- Low runtime risk. Primary risk is losing development workflow helpers.

Fallback:
- Keep scripts archived outside runtime package if needed later.

Tracking doc: `docs/REMOVAL_01_RUNTIME_GOVERNANCE.md`

Status: `approved` (2026-02-20)

## 2. Remove legacy compatibility shims and one-off dispatch paths

Scope:
- Ad hoc branches that preserved old naming/protocol behavior.

Why:
- They make behavior non-obvious and increase regression surface.

Risk:
- Medium if callers still depend on old payload shapes.

Fallback:
- Provide explicit migration notes and one temporary adapter layer.

Tracking doc: `docs/REMOVAL_02_COMPAT_SHIMS_DISPATCH.md`

Status: `approved` (2026-02-20)

## 3. Remove duplicated abstractions and merge authority boundaries

Scope:
- Cases where world/action/execution responsibilities are duplicated.

Why:
- Duplicated code paths cause drift and contradictory behavior.

Risk:
- Medium due to refactor churn.

Fallback:
- Keep strict tests around action semantics and invocation accounting.

Tracking doc: `docs/REMOVAL_03_BOUNDARY_MERGE.md`

Status: `approved` (2026-02-20)

## 4. Remove dashboard frontend sprawl

Scope:
- Many panel-specific JS modules and weakly coupled visualization code.

Why:
- High maintenance cost for low decision-making value.

Risk:
- Low-medium (possible loss of niche views).

Fallback:
- Preserve raw event endpoints so richer UI can be rebuilt later.

Tracking doc: `docs/REMOVAL_04_DASHBOARD_SPRAWL.md`

Status: `approved` (2026-02-20)

## 5. Remove non-essential dormant subsystems from core boot path

Scope:
- Experimental features not required for baseline autonomous economy loop.

Why:
- Reduces startup complexity and hidden coupling.

Risk:
- Medium if some experiments are actually used in production runs.

Fallback:
- Feature-flag and isolate as optional extensions.

Tracking doc: `docs/REMOVAL_05_DORMANT_BOOT_SUBSYSTEMS.md`

Status: `approved` (2026-02-20)

## 6. Remove full backward config compatibility requirement

Scope:
- Stop supporting every historical key and implicit default.

Why:
- Enables clear schema, predictable behavior, and fewer silent misconfigurations.

Risk:
- Medium for migration friction.

Fallback:
- Provide migration map and explicit validation errors.

Tracking doc: `docs/REMOVAL_06_BACKWARD_CONFIG_COMPAT.md`

Status: `approved` (2026-02-20)

---

## Review Protocol

For each removal item we record:
1. What code was removed.
2. What replaced it (if anything).
3. What tests prove no critical regression.
4. Whether to keep an archive path for historical reference.
