# Plan #14: Luna Behavioral Feasibility Repair

**Status:** Live execution complete — invalid pair; redesign not authorized
**Type:** evaluation design
**Priority:** High
**Blocked By:** Plans #12 and #13 complete
**Blocks:** Any replicated Luna cognition comparison

## Goal

Implement Evaluation 14 as a new-number assay that treats the observed 14-call
balanced trajectory plus scarcity boundary as valid and prevents local action
substitution from obscuring selected-action failures.

## Next vertical

Provider-free implementation only:

1. add evaluation-only `fail_closed_no_substitute` action handling;
2. align mint availability with the advertised legal schema while preventing
   auxiliary scorer calls;
3. freeze prescribed/minimal acknowledgements, seed, budget, distribution,
   fourteen-call ceiling, and fifteenth pre-dispatch boundary;
4. validate receipt/status/checkpoint equality and corruption controls; and
5. push the immutable zero-provider preflight revision for review.

## Non-goals

- No Evaluation 12 rerun or evidence mutation.
- No Luna call, behavioral effect threshold, replicated sample, dashboard
  redesign, production parameter, or ordinary-simulation fallback change.

## Acceptance for this design increment

- [x] New evaluation number and seed are used.
- [x] Success, invalidity, non-claims, action failure, receipt, and reset
      boundaries are explicit.
- [x] Exact future exposure is 28 serial provider calls maximum.
- [x] Implementation and live authorization remain separate gates.

## Provider-free implementation receipt

- The typed loop policy defaults to `recovery_fallback`, preserving ordinary
  simulations. Evaluation 14 projects `fail_closed_no_substitute` so a failed
  selected action is logged as the result and no replacement action executes.
- The Evaluation 14 runtime projection enables the mint because it remains an
  advertised legal action, delays its auction beyond the run horizon, and sets
  scorer budget to zero so the mint cannot add provider calls.
- Both cell acknowledgements are frozen in the design and explicitly rejected
  by the live entry point until separate execution authorization is granted.
- `behavioral_feasibility_repair.validate_design_file` checks the seed, budget,
  balanced 7/7 fourteen-call horizon, fifteenth pre-dispatch boundary, 28-call
  maximum exposure, and non-substitution controls without contacting a model.
