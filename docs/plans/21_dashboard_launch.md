# Plan #21: Fixed-Profile Dashboard Launch

**Status:** In Progress
**Type:** prototype vertical
**Priority:** Critical
**Blocked By:** None
**Blocks:** Another operator-observed run

## Gap

**Current:** Brian can inspect preserved ecologies in the dashboard, but must
use the CLI to create another run.

**Target:** The existing archive dashboard exposes one clear fixed-profile
launch action. It shows Luna Medium, Minimal cognition, two agents, the 14-call
ceiling, and 0.033192 resource budget per agent before starting the canonical
worker paused. The browser then opens that worker's live Ecosystem view at
0/14; only the existing Resume control can dispatch Luna.

**Why:** This is the shortest user-visible step from a preserved demonstration
to a repeatable local workbench.

## References Reviewed

- `docs/MVP_ROADMAP.md` - canonical outcome, order, and success criterion
- `scripts/run_recoverable_evaluation.py` - frozen Plan 19 contract and canonical paused `_spawn` path
- `src/agent_ecology3/dashboard/server.py` - existing archive and live UI/API seams
- `tests/test_recoverable_poc.py` - lifecycle, launch, and dashboard preservation evidence
- `CLAUDE.md` - repository workflow and coordination rules

## Files Affected

- `scripts/run_recoverable_evaluation.py` (modify)
- `src/agent_ecology3/dashboard/server.py` (modify)
- `tests/test_recoverable_poc.py` (modify)
- `docs/plans/21_dashboard_launch.md` (create)
- `docs/plans/CLAUDE.md` (modify)
- `docs/MVP_ROADMAP.md` (modify after acceptance)

## Implementation Order

1. Expose the frozen launch profile and launch action through the existing dashboard API.
2. Route launch to `_spawn(..., start_running=False)` with a new durable run directory and fixed worker port.
3. Add one profile confirmation surface and navigate to the returned live dashboard URL.
4. Keep archive selection, replay, Evidence, and matched-pair Comparison unchanged.
5. From a pushed revision, launch in Chromium and prove paused 0/14 with zero provider dispatches.

## Acceptance Criteria

- [ ] The archive dashboard shows one `New paused run` action and the exact fixed profile.
- [ ] Launch uses the canonical Plan 19 profile and creates a new durable run directory.
- [ ] The browser reaches the existing live Ecosystem view without a CLI command.
- [ ] The live view shows Luna Medium, 0/14 calls, the resource exposure, and paused custody.
- [ ] Provider dispatch count remains zero until explicit Resume.
- [ ] Archive replay and Evidence remain reachable; launch failure is visible.

## Non-goals

- Resuming or spending Luna calls as part of acceptance.
- Configurable profiles, scenario editing, graphs, databases, deployment, or production hardening.

## Likely Failure Modes

- The UI bypasses `_spawn` and creates a second lifecycle implementation.
- Launch accidentally sets `start_running` or otherwise dispatches before Resume.
- A port/preflight failure strands the button without an actionable message.
- Navigation loses the existing live Ecosystem controls or hides model/exposure.
- Archive replay, Evidence, or matched-pair Comparison becomes unreachable.
