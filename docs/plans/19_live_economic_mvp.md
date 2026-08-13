# Plan #19: Live Economic MVP Vertical

**Status:** Provider-free vertical complete — authentic Luna execution gated
**Type:** prototype vertical
**Priority:** Critical
**Blocked By:** None for local implementation; authentic execution requires exact call authorization
**Blocks:** Agent Ecology 3 MVP observation

## Outcome

Extend the existing Ecosystem dashboard from completed-run replay to one live,
two-agent Minimal-mode Luna Medium run with an inspectable value-bearing
cross-agent interaction and reusable artifact.

The canonical outcome, acceptance criteria, critical path, and failure
dispositions are owned by [the MVP roadmap](../MVP_ROADMAP.md). This plan owns
their implementation; it must not narrow them silently.

## Adopted decisions

- One Minimal condition is the MVP; another prescribed/minimal comparison is
  outside the critical path.
- Reuse the existing `World`, recoverable runner, dashboard, structured Luna
  action contract, and `llm_client` trace/receipt seam.
- The scenario may provide discoverable, legal, affordable economic
  opportunities. It must not force the model's selected action.
- An interaction graph and broader AE2 dashboard parity are deferred until a
  useful live run creates relationships worth visualizing.
- No WebSocket migration, production hardening, replicated evaluation, causal
  claim, or mint-scoring expansion belongs to this prototype.

## Implementation order

### Slice A — live operator adoption (provider-free)

1. Project live `World.get_state_summary()` and canonical events through the
   existing operator contract.
2. Keep Ecosystem visible across paused, running, stopped, completed, and
   invalid states.
3. Preserve Resume, Pause, Stop, recovery state, Comparison, Evidence, and
   completed-run replay.
4. Browser-observe paused -> running -> completed with a provider-free fixture.

### Slice B — economically legible scenario (provider-free)

1. Freeze two principals, Minimal cognition, hard call ceiling, starting
   resources, and discoverable cross-principal opportunities.
2. Prove intended reads/transfers are authorized, visible, and affordable.
3. Prove no fixture, fallback, or scenario hook manufactures the counted
   economic action.
4. Freeze the exact execution acknowledgement, source/client revisions, and
   maximum Luna exposure.

### Slice C — authentic MVP observation (separately authorized)

1. Start from the reviewed clean pushed revision, paused.
2. Open the dashboard, resume once, and observe the run to its hard cap.
3. Preserve traces, receipts, actions, balances, artifacts, browser evidence,
   and terminal replay.
4. Continue, repair, or stop using the roadmap failure dispositions.

## Execution gate

No Luna call is authorized by this plan. After Slices A–B and the zero-provider
preflight pass, present the exact model, acknowledgement, hard call ceiling,
maximum exposure, and clean revisions for Brian's approval.

The reviewed command shape is:

```bash
python3 scripts/run_recoverable_evaluation.py start \
  --acknowledgement plan19/luna-medium/live-economic-mvp/v1 \
  --run-id plan19_luna_live_economic_mvp_v1 \
  --target-attempts 14 \
  --starting-llm-budget 0.033192 \
  --principal-count 2 \
  --cognition-mode minimal \
  --policy-seed 24190 \
  --port 9019
```

`start` is paused by default. Do not use `--start-running` for the authentic
MVP observation.

## Required acceptance

- All MVP acceptance criteria in `docs/MVP_ROADMAP.md` pass.
- Focused API/runner tests and one authentic browser journey cover the changed
  live path; broad UI parity and production checks remain out of scope.
- The completed receipt and dashboard agree on action count, principals,
  balances, artifacts, lifecycle, recovery, and failure/fallback state.

## Likely failure modes

- Live UI accidentally consumes the completed-review projection rather than
  the running `World`.
- Condition/view controls mutate each other or disappear across lifecycle
  transitions.
- Access contracts make advertised cross-agent opportunities unreadable.
- Agents repeatedly query because opportunity metadata is not discoverable.
- Internal budget and independent provider ceiling are conflated again.
- A failed model-selected action is replaced by a local substitute and appears
  economically successful.

## Provider-free development receipt

- The live `/operator-state` projection now consumes the running `World` and
  canonical events; completed-run replay still uses the same operator contract.
- Artifact discovery exposes `read_price` and `invoke_price`, so Luna can see
  whether a readable opportunity is economically relevant.
- Two ordinary freeware artifacts, one owned by each principal and each priced
  at 2 scrip, are seeded as scenario opportunities. Their metadata explicitly
  marks them as fixtures, and seeding emits no agent-action event.
- A scripted structured-action fixture exercised the real runner and action
  path with zero provider calls. It produced one cross-agent purchase, balances
  of 102/98 from 100/100, no fallback, and a paid activity row in the dashboard.
  This validates plumbing only; it is not evidence that Luna will choose the
  purchase.
- Fresh Chromium at 1440×900 observed paused (0/2, 100/100), running (1/2), and
  completed (2/2, 102/98) states in the existing Ecosystem dashboard.
- The full repository suite passes 145 tests against the clean, reviewed
  `llm_client` revision `286715784f1d535d6dfcd2c867ca678d666e27d5`. The
  general active client checkout is not the execution authority for this plan.
- The browser journey reproduced and closed two lifecycle defects before any
  Luna spend: paused wall time consumed the active duration, and a heartbeat
  race could relabel a fully committed run as stopped. Active runtime now
  excludes paused time, and terminal custody is derived from durable committed
  attempts with `invalid` remaining authoritative.
- The remaining Slice C gate is an authentic Luna Medium run. Its counted
  actions must be model-selected; the provider-free scripted purchase cannot
  satisfy MVP acceptance.
