# Plan #18: Ecosystem Operator Dashboard

**Status:** Complete
**Type:** implementation
**Priority:** High
**Blocked By:** None
**Blocks:** Useful human observation of an Agent Ecology run

---

## Gap

**Current:** The dashboard reports a paired experimental conclusion, but it does not let a reviewer inhabit the run: agents, their resources, created artifacts, and unfolding actions are not an explorable primary workflow.

**Target:** Restore the core AE2 operator loop in AE3: select a condition, replay decisions, inspect agents and resources, follow activity, search artifacts, and open artifact detail. Keep Comparison and Evidence as secondary views.

**Why:** The stakeholder wants to observe the ecology, not only read a result summary.

---

## UI Contract

- **User:** Brian reviewing an authentic Luna Medium PoC run.
- **Repeated task:** Understand what each agent did, what changed, and what it produced.
- **Critical flow:** Open dashboard -> choose Minimal -> Play/scrub run -> select an artifact -> inspect its content and ownership.
- **Canonical exemplar:** AE2 Agents, Artifacts, Activity, progress controls, and detail modal.
- **Data boundary:** Real AE3 receipt plus canonical JSONL events through one `/operator-state` projection.
- **Continue criterion:** The replay makes Minimal's six writes and cross-agent reads understandable without opening raw JSON.
- **Stop/revise criterion:** The reviewer still needs raw records to explain agent behavior.

### Preservation Matrix

| Entry point/state | Surface | Disposition |
|---|---|---|
| Completed pair `/` | Ecosystem operator | New default |
| Completed pair `/` | Paired comparison | Preserve as `Comparison` tab |
| Completed pair `/` | Raw state/events | Preserve as `Evidence` tab |
| Live `/` | State, events, Resume/Pause/Stop | Preserve; operator projection can follow in a later increment |

---

## References Reviewed

- `agent_ecology2/src/dashboard/static/index.html` - agents/artifacts/activity/progress information architecture
- `agent_ecology2/src/dashboard/static/js/panels/{agents,artifacts,activity}.js` - drill-down and filtering behavior
- `src/agent_ecology3/dashboard/server.py` - canonical AE3 dashboard owner
- `src/agent_ecology3/world/world.py:get_state_summary` - live state boundary
- `docs/REMOVAL_04_DASHBOARD_SPRAWL.md` - prevent optional panel-fleet and duplicate-stack regression
- `docs/plans/17_useful_run_review.md` - comparison and evidence surfaces to preserve

---

## Files Affected

- `src/agent_ecology3/dashboard/server.py` (modify)
- `tests/test_recoverable_poc.py` (modify)
- `docs/plans/18_ecosystem_operator.md` (create)
- `docs/plans/CLAUDE.md` (modify)

---

## Plan

1. Add one receipt/event-derived operator projection for agents, artifacts, and decisions.
2. Add stable Ecosystem, Comparison, and Evidence navigation.
3. Make Ecosystem default with condition selection, replay/scrubber, agent cards, activity feed, artifact search, and artifact detail.
4. Verify the critical flow against authentic Eval 15 data in a fresh browser.

---

## Non-goals

- AE2 network/dependency/temporal graphs, charts, exports, alerts, or global search
- WebSocket migration or production performance work
- Mobile-specific layout beyond avoiding breakage
- Claiming economic interaction that did not occur

---

## Acceptance Criteria

- [x] Ecosystem is the default completed-run view
- [x] Condition selection does not change the selected view
- [x] Replay/scrubbing updates activity and created artifacts through the selected decision
- [x] Both agents show resource and action state
- [x] Artifact search and detail work on authentic agent-created artifacts
- [x] Comparison and Evidence remain reachable
- [x] Focused API/UI test, full suite, and authentic browser flow pass

## Verification

- `/operator-state?run=minimal` exercised through the focused integration test.
- Full repository suite passed (142 tests); Ruff and mypy passed.
- Fresh Chromium at 1440×1000 replayed from Decision 0, paused, scrubbed to Decision 14, opened `alpha_1_plan`, switched among all three views, refreshed the canonical URL, and reported no console errors or failed requests.
