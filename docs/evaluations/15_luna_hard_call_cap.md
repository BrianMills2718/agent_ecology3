# Evaluation 15: Luna Hard Call Cap

**Stage:** MVP matched-pair feasibility
**Execution:** Completed 2026-08-13; MVP matched pair valid
**Predecessor:** Evaluation 14 invalid because budget exhaustion allowed minimal call 15

## Outcome

Run one dashboard-visible prescribed/minimal pair with identical exposure. Each
cell commits exactly fourteen Luna Medium calls, balanced 7/7 across two
principals, then completes normally because the runner target is the hard call
cap. Remaining LLM budget is descriptive and does not control the horizon.

The result can establish only that the MVP can present an inspectable matched
pair with correct custody. It cannot establish a behavioral effect, causality,
reliability, optimal budget, or a production parameter.

## Frozen contract

- new seed `24150`; prescribed first, minimal second;
- starting budget `0.033192` per principal;
- exact target and provider ceiling: fourteen calls per condition;
- required distribution: `alpha_1=7`, `alpha_2=7`;
- Luna Medium, medium reasoning, CLI transport, structured actions;
- `fail_closed_no_substitute`, zero retries, no fallback model, no MCP;
- mint enabled, auction beyond the horizon, scorer budget zero;
- checkpoint, status, receipt, and dashboard agree that the target was reached,
  with no terminal reason. The runner may label its intentional target stop
  `stopped` while the recovery coordinator labels the final commit `completed`;
  exact counts and terminal reason govern this prototype readout.

If prescribed is invalid, minimal is suppressed. Maximum external exposure is
28 serial calls. No rerun or replacement evaluation is authorized by this
document.

## Readout

Both prescribed and minimal committed exactly fourteen Luna calls, balanced
7/7, with fourteen shared-client receipts, no retry/model fallback/MCP, and no
local substitute actions. Total exposure was exactly the authorized 28 calls.
Prescribed retained lifecycle `completed`; minimal retained `stopped` after the
intentional runner target. Both have no terminal reason, and their embedded
receipt/checkpoint/status counts agree.

This is the first valid dashboard-visible matched pair on the repaired Luna
route. It proves MVP run and custody feasibility only. The observed action
trajectories remain descriptive and do not establish a cognition effect.
