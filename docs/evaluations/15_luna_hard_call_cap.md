# Evaluation 15: Luna Hard Call Cap

**Stage:** MVP matched-pair feasibility
**Execution:** Authorized; evidence pending
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
- checkpoint, status, receipt, and dashboard all report completed custody.

If prescribed is invalid, minimal is suppressed. Maximum external exposure is
28 serial calls. No rerun or replacement evaluation is authorized by this
document.
