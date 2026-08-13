# Plan #13: Receipt and Fallback Contract Repair

**Status:** Complete — receipt fixed; fallback contract diagnosed
**Type:** focused implementation and diagnosis
**Priority:** High
**Blocked By:** Evaluation 12 terminal evidence
**Blocks:** Any new behavioral evaluation

## Observed failures

Evaluation 12 exposed two independent instrument failures:

1. `run_receipt.json` retained lifecycle `running` while its embedded checkpoint
   and durable status correctly reported the terminal scarcity stop.
2. Three loop decisions used recovery fallback despite the evaluation's
   no-fallback validity rule.

## Root causes

The receipt writer ran before the heartbeat published its computed terminal
lifecycle. The shutdown path also wrote a final receipt without first
normalizing and publishing terminal status.

The fallback markers are truthful. One Luna action tried to read another
principal's private strategy and failed access before recovery wrote scratch.
Two Luna actions submitted to mint while the recoverable runner had disabled
mint even though the legal prompt still advertised `submit_to_mint`; recovery
then substituted another action. In two records the logged result describes
the recovery action, which can hide the original failure unless the fallback
fields are inspected.

## Repair boundary

- Publish terminal status before every terminal receipt write.
- Add focused regression evidence that terminal status appears in the receipt.
- Preserve existing fallback behavior for ordinary simulations.
- Do not make a new evaluation valid by relabeling fallback.
- Before another behavioral evaluation, align advertised legal actions with
  runtime availability and add an evaluation-only fail-closed policy that
  retains the original action failure without executing a substitute action.

The last item belongs to the next new-number evaluation implementation because
it changes experimental behavior and requires its own frozen contract.

## Acceptance

- [x] Terminal receipt and durable status agree on lifecycle and reason.
- [x] Focused recovery tests, mypy, and Ruff pass.
- [x] Evaluation 12 remains immutable and invalid.
- [x] Fallback causes and required future boundary are documented.
