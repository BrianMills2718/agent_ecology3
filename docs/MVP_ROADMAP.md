# Agent Ecology 3 MVP Roadmap

```yaml
doc_role: active_authority
authority: canonical
status: active
created: 2026-08-13
updated: 2026-08-13
```

This is the current-direction front door for the Agent Ecology 3 MVP. Completed
plans and evaluations remain evidence; they do not define the next priority.

## MVP outcome

For Brian as the operator, change a preserved-run replay into a live,
inspectable two-agent ecology: launch one bounded Luna Medium run, resume it in
the dashboard, watch both agents act and resources change, observe at least one
successful cross-agent value-bearing interaction and one reusable artifact,
then inspect the completed run in the same interface.

Delivery maturity is **local prototype**. This is not a behavioral comparison,
production service, or claim that emergence generalizes.

## Observation status

| Dimension | Current truth |
|---|---|
| Technical execution | Luna Medium route, structured actions, recovery, detached lifecycle, and hard call caps pass |
| Reviewability | Completed Eval 15 runs open in the Ecosystem operator dashboard with replay and artifact inspection |
| Stakeholder observation | Partial: the dashboard is "at least somewhat understandable" |
| MVP outcome | **Not yet observed**: the operator view is not wired to a live run, and Eval 15 produced no transfer, paid purchase, mint submission, or scrip movement |

The canonical outcome probe is a local dashboard session starting paused and
ending with a replayable completed run. Tests, traces, and receipts support the
probe but do not replace Brian's observation of it.

## Critical path

| Order | Goal | Class | State | Exit evidence |
|---|---|---|---|---|
| 1 | Feed the existing Ecosystem panels from the running `World` and preserve Resume/Pause/Stop/recovery | direct blocker | selected | Fresh browser observes paused -> running -> completed with live agents, activity, artifacts, and resources |
| 2 | Provide one Minimal-mode, two-agent scenario with discoverable priced/cross-agent opportunities without prescribing the selected actions | vertical | selected; bounded design next | Provider-free fixture proves opportunities are legal, visible, affordable, and not forced |
| 3 | Execute one authentic capped Luna Medium run through that scenario | vertical | blocked on exact call authorization after implementation review | Dashboard visibly shows at least one successful value-bearing cross-agent action and one reusable artifact; receipt has exact custody and no retry/fallback/MCP |
| 4 | Repair only a failure reproduced by the authentic probe, then repeat only if its result can change the continue/stop decision | conditional | deliberately deferred | Focused evidence closes the observed boundary |
| 5 | Add an interaction graph synchronized with live/replay state | optional | deliberately deferred | Resume only after a run contains relationships worth visualizing and the graph would improve operator judgment |

Plan 19 owns goals 1–3. They are one sequential prototype vertical; no work-unit
graph or parallel coordination artifact is needed.

## Binding implementation order

1. Extend the existing dashboard/API seam; do not create another dashboard.
2. Prove live operator projection provider-free with the current runner.
3. Freeze the smallest economically legible scenario and its mutation checks.
4. Run the exact browser journey against the implementation revision.
5. Request approval for the exact Luna call ceiling and acknowledgement.
6. Execute once, preserve the receipt, and assess the visible result.

Reversible local implementation choices proceed without repeated approval.
Pause for a change to the MVP outcome, a new external/shared boundary, or the
exact multi-call Luna authorization.

## MVP acceptance

- A single command starts the run paused and exposes the dashboard URL.
- Ecosystem is the live default; agents, action feed, artifacts, balances,
  budget, lifecycle, and recovery update during the run.
- Resume, Pause, and Stop remain usable and machine-accessible.
- The model—not a local fallback—selects all counted actions.
- At least one successful paid read, scrip transfer, or LLM-budget transfer
  crosses principals.
- At least one agent-created reusable artifact is visible and inspectable in
  the dashboard.
- The run stops at the authorized hard call ceiling with exact trace/receipt
  custody, zero retry/model fallback/MCP, and a replayable terminal state.
- Brian can explain what happened without opening raw JSON.

## Failure dispositions

| Observed failure | Disposition |
|---|---|
| No economic interaction | Revise scenario discoverability/access/affordability or horizon; do not add visualization |
| `not_authorized` blocks intended opportunity | Repair the access-contract/scenario boundary |
| Dashboard lags or disagrees with receipts | Repair the live projection/adoption seam before another model run |
| Budget permits excess calls or stops before the frozen horizon | Keep the independent hard call ceiling authoritative; revise budget separately |
| Retry, fallback, MCP, ambiguous dispatch, or replacement call | Mark the run invalid and stop |
| Useful live run but relationships remain hard to understand | Promote the synchronized interaction graph into the next goal |

## Authority and history

- [Plan 19](plans/19_live_economic_mvp.md) is the selected active goal.
- [Plan index](plans/CLAUDE.md) is navigation and historical status.
- [Evaluation 15](evaluations/15_luna_hard_call_cap.md) proves bounded run and
  custody feasibility only.
- [Plan 18](plans/18_ecosystem_operator.md) provides the completed-run operator
  surface that Plan 19 will extend live.
- [Lineage and restarts](LINEAGE_AND_RESTARTS.md) remains authoritative for
  AE1/AE2/AE3 lineage and restart failure history.
