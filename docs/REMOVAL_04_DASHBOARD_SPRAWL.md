# Removal 04: Dashboard Frontend Sprawl

Date: 2026-02-20
Status: `approved` (approved by user on 2026-02-20)

## Decision Draft

Do not port the AE2 monolithic multi-panel frontend into AE3. Keep a minimal observability surface centered on JSONL event/state streams and a thin API, and defer non-essential visualization modules until they are explicitly justified.

## Evidence From `agent_ecology2`

1. Static dashboard bootstraps many independently-evolved panel scripts from one HTML file:
- `agent_ecology2/src/dashboard/static/index.html:472`
- `agent_ecology2/src/dashboard/static/index.html:489`

2. Frontend initialization path in one `Dashboard` object conditionally wires many optional modules and toggle systems:
- `agent_ecology2/src/dashboard/static/js/main.js:13`
- `agent_ecology2/src/dashboard/static/js/main.js:43`
- `agent_ecology2/src/dashboard/static/js/main.js:114`

3. Large panel surface area with mixed coupling points:
- `agent_ecology2/src/dashboard/static/js/panels/activity.js`
- `agent_ecology2/src/dashboard/static/js/panels/network.js`
- `agent_ecology2/src/dashboard/static/js/panels/dependency-graph.js`
- `agent_ecology2/src/dashboard/static/js/panels/temporal-network.js`
- `agent_ecology2/src/dashboard/static/js/panels/emergence.js`
- `agent_ecology2/src/dashboard/static/js/panels/thinking.js`

4. Prior audit already documented parallel/partially-disconnected dashboard architectures and dead paths:
- `agent_ecology2/docs/plans/307_dashboard_audit.md:1`

## AE3 Current Reality

AE3 currently has placeholder directories for `dashboard/` and `simulation/`, but no implementation files in those paths yet:
- `agent_ecology3/src/agent_ecology3/dashboard`
- `agent_ecology3/src/agent_ecology3/simulation`

So this removal is primarily a "do not reintroduce sprawl during rebuild" policy decision at this stage.

## Proposed Keep vs Remove for AE3

Keep:
1. Canonical JSONL logs and a narrow API surface for state/events.
2. One compact status view for run health, budgets, and key counters.
3. Contract-aware artifact inspection that reuses backend authority checks.

Do not port:
1. Multi-panel script fleet pattern from AE2 static frontend.
2. Optional panel initialization via repeated `typeof ... !== 'undefined'` gating.
3. Feature-specific visual modules unless they are tied to an active operator decision.
4. Duplicate dashboard generations (parallel v1/v2 UI stacks).

## Acceptance Criteria (for implementation phase)

1. AE3 dashboard path has a single bounded UI implementation (or none initially), not a panel zoo.
2. Every exposed UI metric maps to one backend canonical event/state source.
3. No duplicate route stacks for equivalent dashboard data.
4. Integration tests cover core dashboard API contracts (state snapshot + event tail).

## Risks

1. Some niche views may be temporarily unavailable.
2. Team may miss ad-hoc visual diagnostics from legacy panels.

## Mitigation

1. Preserve machine-readable event/state outputs so visualizations can be re-added incrementally.
2. Reintroduce any missing view only after a concrete operator use-case is documented.

## Next Step

Approved. Next step is removal #5 review (dormant subsystems in core boot path).
