# Agent Ecology 3 Rewrite Scope

Date: 2026-02-20

This document records the agreed direction for rebuilding `agent_ecology2` as a fresh `agent_ecology3`.

## Keep

These concepts stay, but implementation is simplified:

1. Artifact-centric kernel (`World`, typed actions, action execution).
2. Principals + scrip economy.
3. Resource constraints (LLM budget, disk quota, rate-limited resources).
4. Contract-based permissions (kernel contracts + executable contracts).
5. Executable artifacts and invoke flow.
6. Delegation-based charging for invoke costs.
7. Mint systems (auction + task mint).
8. JSONL event log as source of truth.
9. Autonomous behavior via `has_loop` executable artifacts.

## Add / Improve

1. Cleaner module boundaries and fewer cross-cutting abstractions.
2. Pydantic-validated config model with tighter defaults.
3. Principal-scoped kernel interfaces exposed to artifact code.
4. Small kernel service layer (`kernel_act`, `kernel_mint`, `kernel_delegation`, `kernel_time`).
5. Better safety defaults (LLM budget guardrails, model allowlist, explicit rate checks).
6. Lean dashboard/API focused on observability and control basics.
7. Focused tests for kernel actions, simulation loop, and dashboard API.
8. Single `run.py` entrypoint for simulation/dashboard workflows.

## Remove

1. Governance/meta-process tooling from runtime path.
2. Worktree/plan orchestration code unrelated to simulation behavior.
3. Legacy compatibility shims and one-off pathways.
4. Over-fragmented dashboard panel surface and heavy frontend sprawl.
5. Duplicated abstractions that split one responsibility across many modules.
6. Non-essential legacy feature scaffolding that is not actively used by the kernel loop.

## Non-Goals

1. Full backward compatibility with all `agent_ecology2` config keys and APIs.
2. Porting every experimental subsystem before core kernel quality is stable.
3. Preserving old internal file layout.
