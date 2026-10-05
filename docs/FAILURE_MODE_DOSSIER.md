# Agent Ecology Failure-Mode Dossier

```yaml
doc_role: historical_failure_authority
status: current
scope: agent_ecology, agent_ecology2, agent_ecology3
reviewed: 2026-08-23
purpose: design constraints and recurring audit baseline for a simplified Agent Ecology
```

## Purpose and authority

This dossier preserves what went wrong across Agent Ecology 1, 2, and 3 so a
new implementation does not learn only the attractive parts of the lineage. It
is the detailed companion to [Lineage and Restarts](LINEAGE_AND_RESTARTS.md).

Use it in two ways:

1. as negative requirements when designing the simplified ecology; and
2. as a named failure catalogue in design, implementation, run-validity, and
   periodic architecture audits.

This document records project evidence and **candidate audit requirements**. It
does not itself change Company Planning, AES, Project Meta lifecycle status, or
cross-project policy. Those systems may adopt the audit contract by explicit
change in their own authority.

Failure modes remain in the register after repair. A repaired incident becomes
a regression invariant; it does not become irrelevant history.

## Evidence method and boundary

### Evidence labels

- **O — observed incident:** a run, retained receipt, source execution, or test
  directly exhibited the failure.
- **S — structural observation:** current or historical source contains the
  mechanism that creates the risk.
- **D — documented diagnosis/decision:** an accepted project record names the
  failure or restart reason.
- **I — inference/watch item:** evidence supports the risk, but no retained
  incident proves that it caused a result. Audits must not report an inference
  as a historical failure.

### Repair states

- **Open:** the underlying question or defect remains unresolved.
- **Repaired; retain regression:** a later change directly closed the incident,
  but every relevant audit must continue proving the invariant.
- **Bounded:** acceptable only inside the stated prototype or experiment scope.
- **Historical:** frozen predecessor behavior; do not port it accidentally.

### Revision ledger

| Line | Revision(s) reviewed | Role in this synthesis |
|---|---|---|
| AE1 | [`7209207`](https://github.com/BrianMills2718/agent_ecology/tree/720920732373292d1353be9a1f8066016b6f5aa8) | Sole commit and immutable source snapshot. |
| AE2 | [`33bbb6d`](https://github.com/BrianMills2718/agent_ecology2/tree/33bbb6de0142435412c02316bd5a43f5733954d8), checked against local `2328f8e` | Frozen lineage review plus current source/history check. The later local revision changes instruction/UI metadata, not the cited historical mechanisms. |
| AE3 | `bef4eeec72d09b2cd768124181d872afbfa81b75` | Current source, plans, evaluation records, and repair history at dossier creation. |

The synthesis uses repository source and tracked evidence records. Locally
retained run directories named by AE3 plans were not treated as independently
portable evidence unless a tracked evaluation or sign-off reconciled them.

## Executive failure register

| ID | Failure mode | Lines | Evidence | Repair state |
|---|---|---|---|---|
| FM-01 | Designer-installed behavior presented as emergence | AE1–AE3 | O/S/D | Open empirical question |
| FM-02 | The actor implementation does not match the claimed agent boundary | AE1, AE3 | S/D | Open for simplified design |
| FM-03 | Copy-forward versions duplicate the authority surface | AE1 | S | Historical |
| FM-04 | A runnable demo or summary is mistaken for durable evidence | AE1, AE3 | O/S | Partly repaired; retain regression |
| FM-05 | Substrate breadth grows faster than a stable vertical | AE2, AE3 | S/D | Recurring watch item |
| FM-06 | Parallel owners, shims, compatibility, and dormant paths split authority | AE2 | S/D | Repaired by AE3 scope; retain regression |
| FM-07 | A custom agent framework duplicates mature runtime capabilities | AE2, AE3 | S/D | Open architecture decision |
| FM-08 | Agent-visible guidance drifts from the runtime contract | AE2 | O | Repaired incident; retain regression |
| FM-09 | Small schema/observation defects cause ecology-wide paralysis | AE2 | O | Repaired incident; retain regression |
| FM-10 | Scarcity or interdependence does not actually bind | AE2, AE3 | O | Open experimental control |
| FM-11 | Plumbing and activity metrics are promoted as thesis evidence | AE2, AE3 | D/O | Open interpretation risk |
| FM-12 | A synchronous provider boundary blocks async control | AE3 | O | Repaired; retain regression |
| FM-13 | Provider formatting/reliability failure is counted as agent behavior | AE3 | O | Repaired instrument; retain regression |
| FM-14 | Trace linkage is mistaken for full evidence custody | AE3 | O | Repaired; retain regression |
| FM-15 | An assay assumes metadata outside the public contract | AE3 | O | Repaired; retain regression |
| FM-16 | Paid-worker lifetime or cwd inherits an interactive/worktree lifecycle | AE3 | O | Repaired; retain regression |
| FM-17 | Provider settlement, decision, and custody are not atomic | AE3 | O | Repaired bounded path; retain fault injection |
| FM-18 | A fallback action masquerades as authentic agent behavior | AE3 | O | Repaired authentic path; retain regression |
| FM-19 | Conditions receive unequal call exposure because scarcity and prompts interact | AE3 | O | Repaired with hard cap; retain parity gate |
| FM-20 | Provider billing semantics make simulated economic scarcity non-binding | AE3 | O/S | Bounded by internal charge model |
| FM-21 | Missing observation memory produces repetitive or falsely attributed adaptation | AE3 | O | Repaired bounded path; retain regression |
| FM-22 | Agent/runtime policy complexity reconcentrates in a generated monolith | AE3 | S/I | Open watch item |
| FM-23 | Global serialization silently defines ecology timing | AE3 | S/I | Open watch item |
| FM-24 | Process and presentation grow around an unresolved experiment | AE2, AE3 | S/D | Recurring watch item |

## Detailed failure records

### FM-01 — Designer-installed behavior presented as emergence

**Mechanism.** A rule, role, prompt, forced-exploration policy, objective cycle,
fallback, or seeded interaction directly selects the behavior later described
as emergent.

**Evidence.** AE1 hard-codes grudge memory and reciprocity refusal in
[`world_v2.py`](https://github.com/BrianMills2718/agent_ecology/blob/720920732373292d1353be9a1f8066016b6f5aa8/world_v2.py); the resulting feud
network proves the rule's dynamics, not its discovery. AE2's smoke agents were
given explicit cross-agent tasks and elaborate archetype/state-machine prompts,
yet produced almost no cooperation ([simulation learnings](https://github.com/BrianMills2718/agent_ecology2/blob/33bbb6de0142435412c02316bd5a43f5733954d8/docs/SIMULATION_LEARNINGS.md)). AE3 explicitly exposes prescribed/minimal cognition,
forced exploration, action gates, and deterministic fallbacks in
[`config.yaml`](../config/config.yaml) and its generated loop. Evaluation 04
could not complete the ablation, and Evaluation 07 was invalid, so the central
prescription-versus-emergence question remains unresolved. Plan 23 is a valid
one-run candidate, not general evidence.

**Consequence.** Activity can be real while the causal claim is false. More
behavior may mean more designer pressure, not more agent adaptation.

**Recurrence signals.** The success story repeats words from system prompts;
roles predict action types; a fallback/forced-explore share is nonzero; seeded
fixtures already contain the claimed solution; removing instructions removes
all behavior.

**Prevention constraint.** Every behavioral claim needs a minimally
prescriptive matched condition, decision-origin attribution, and an explicit
list of seeded affordances. Do not call designer-selected dynamics emergence.

**Audit probe / fail condition.** Diff prompts, config, seed artifacts, action
gates, and recovery policy between conditions. Fail the claim if the alleged
behavior is directly encoded or if it is counted from anything other than an
authentic model-selected action.

### FM-02 — The actor implementation does not match the claimed agent boundary

**Mechanism.** The project says it studies agents, but the executable actor is a
heuristic or a one-action decision selector whose memory, tools, planning, and
lifecycle are actually owned by ecology code.

**Evidence.** AE1 agents choose from fixed probabilities and acceptance
history; no LLM or autonomous runtime exists. AE3 uses `llm_client` and real
Codex/Luna calls, but the default loop constructs memory, prompts, parsing,
normalization, gating, exploration, recovery, and action execution inside
[`World._default_loop_code`](../src/agent_ecology3/world/world.py). The Luna path
intentionally returns one structured action with no intrinsic tools or MCP, as
documented in [Plan 10](plans/10_luna_medium_recovery_gate.md). Plan 22 explicitly
made replacing principals with Codex agents a non-goal.

**Consequence.** Agent-SDK capability may be paid for but not used, while the
ecology maintains a second custom agent framework. Conclusions may describe
the wrapper's policy more than the agent runtime.

**Recurrence signals.** Ecology code owns a prompt loop, memory service, tool
router, retry logic, parser, planner, or permission model already supplied by
the selected agent runtime; an “agent” cannot continue without generated
ecology-owned code.

**Prevention constraint.** The simplified design must declare exactly what the
agent runtime owns and what the ecology kernel owns. Prefer resident Codex or
Claude agents through `llm_client`; keep economic authority and world mutation
in the kernel.

**Audit probe / fail condition.** Draw the call path from an agent turn to a
world mutation and assign one owner to planning, memory, tools, lifecycle,
permissions, retries, and settlement. Fail architecture review when ownership
is duplicated without a named, tested exception.

### FM-03 — Copy-forward versions duplicate the authority surface

**Mechanism.** A new experiment copies the whole world and changes one policy
instead of isolating an intervention behind a shared seam.

**Evidence.** AE1's `world_v1.py` and `world_v2.py` are 577 and 627 lines and
repeat most of the world to add reciprocity. There is no package boundary or
test suite.

**Consequence.** Comparisons include accidental code drift; fixes and semantics
must be maintained twice; later lineage analysis cannot easily identify the
intervention.

**Recurrence signals.** Files or repositories named `v2`, `new`, or `rewrite`
contain mostly copied code; experimental conditions select different
implementations rather than data/config.

**Prevention constraint.** One kernel implementation, versioned typed configs,
and explicit intervention switches. Fork only at a real authority boundary.

**Audit probe / fail condition.** Compare implementations used by matched
conditions. Fail an experimental design when treatment changes more code than
the preregistered intervention.

### FM-04 — A runnable demo or summary is mistaken for durable evidence

**Mechanism.** A script runs or a README names metrics, but config, source,
events, raw responses, summaries, hashes, and settlement receipts cannot be
reopened together.

**Evidence.** AE1 has one commit, four Python programs, no tests, environment
declaration, Markdown documentation, or retained run receipts. AE3's lineage
review found historical README/handoff claims whose logs and summary JSON were
not tracked in a clean clone. Evaluations 04–07 improved evidence bundles, but
Evaluation 07 still ended without a complete reproduction receipt.

**Consequence.** Results become anecdotes; audits cannot distinguish a real
run from transcription, stale configuration, or changed code.

**Recurrence signals.** Evidence lives only in `logs/latest`, an operator home,
or prose; no source revision or content hash; a clean reader cannot locate the
receipt; dashboard output is the only record.

**Prevention constraint.** Each decision-driving run must retain or durably
reference source revision, config, prompts, model/route, rendered inputs, raw
outputs/tool envelopes, normalized decisions, world events, settlement,
summary, and hashes.

**Audit probe / fail condition.** Reopen from a fresh read-only process and
reconcile receipt, checkpoint, event log, and UI projection. Fail promotion if
any decision fact depends on an unretained interactive session.

### FM-05 — Substrate breadth grows faster than a stable vertical

**Mechanism.** The project generalizes artifacts, contracts, permissions,
workflows, dashboards, governance, and agent variants before one authentic,
decision-useful ecology is stable.

**Evidence.** At the frozen lineage review AE2 had 1,211 commits, 708 tracked
files, 25,864 source lines, 33,916 test lines, and 44,417 Markdown lines. Its
history later removed about 29,000 lines of legacy agents, about 6,800 lines of
a dashboard generation, and about 4,200 lines of dead code. AE3 restarted to
remove six specific classes of breadth (now listed as standing constraints in
[Lineage and Restarts](LINEAGE_AND_RESTARTS.md#standing-constraints-from-the-rebuild)).

**Consequence.** Iteration cost rises while the thesis remains unanswered.
Deleting speculative breadth becomes a project of its own.

**Recurrence signals.** New subsystems have no current consumer; several
framework generations coexist; architecture work repeatedly precedes an
authentic vertical; line count and plan count grow without stronger evidence.

**Prevention constraint.** Keep one canonical ecology example. New abstractions
must protect a reproduced failure or enable the next visible experiment.

**Audit probe / fail condition.** For each new subsystem, name its current
consumer, adoption receipt, and deletion consequence. Defer it when those
cannot be shown.

### FM-06 — Parallel owners, shims, compatibility, and dormant paths split authority

**Mechanism.** The same invariant is enforced through multiple resource,
permission, dispatch, query, accounting, compatibility, or boot paths.

**Evidence.** AE3's accepted AE2 removal records identify runtime-adjacent
governance, compatibility shims, one-off dispatch, duplicated boundaries,
dashboard sprawl, dormant boot subsystems, and backward-config compatibility.
AE2 Plan 299 separately records two agent systems, one of which bypassed the
kernel ([Plan 299](https://github.com/BrianMills2718/agent_ecology2/blob/33bbb6de0142435412c02316bd5a43f5733954d8/docs/plans/299_eliminate_legacy_agents.md)).

**Consequence.** The system cannot state which path is authoritative; tests may
validate one route while a real consumer uses another.

**Recurrence signals.** `legacy`, `compat`, `shim`, `v2`, special-case dispatch,
multiple stores/ledgers, or disabled-by-default systems remain in production
paths without a named caller.

**Prevention constraint.** One owner and one production path per invariant.
Adapters need a current consumer, removal trigger, and integration proof.

**Audit probe / fail condition.** Trace the canonical consumer for each public
action. Fail adoption if a second path mutates the same invariant or if the
tested path is not the consumed path.

### FM-07 — A custom agent framework duplicates mature runtime capabilities

**Mechanism.** The ecology builds its own workflows, state machines, RAG,
memory, prompts, parser, retry/fallback, tool bridge, and lifecycle instead of
configuring an existing agent runtime.

**Evidence.** AE2 Plan 299 describes a roughly 9,000-line legacy agent system;
the deletion commit removed roughly 29,000 lines across agent code, handbooks,
and variants. AE3 is smaller but again embeds an approximately 829-line
generated default loop (`world.py` lines 950–1778) and forwards agent SDK
settings such as cwd, turns, permissions, and MCP while retaining ecology-owned
agent policy.

**Consequence.** Agent behavior changes require kernel changes; mature SDK
features are duplicated inconsistently; the experiment surface becomes hard to
audit.

**Recurrence signals.** Large prompt-code strings; ecology-specific agent base
classes; custom memory/planner/tool frameworks; provider-specific branches in
world code.

**Prevention constraint.** Treat `llm_client` plus the selected headless agent
runtime as the agent capability owner. Keep only typed world tools, economic
settlement, permissions at the world boundary, and run custody in the ecology.

**Audit probe / fail condition.** Inventory code that would disappear if the
agent SDK owned its normal lifecycle. Any retained duplicate needs a concrete
world-invariant reason and an end-to-end test.

### FM-08 — Agent-visible guidance drifts from the runtime contract

**Mechanism.** Prompts, handbooks, skills, or examples name removed primitives
or teach the wrong action boundary.

**Evidence.** AE2 Alpha Prime repeatedly tried to invoke removed
`genesis_ledger`, then reread the stale handbook instead of progressing. The
tracked diagnosis says Plan 254 removed the artifact without updating all
references ([simulation learnings](https://github.com/BrianMills2718/agent_ecology2/blob/33bbb6de0142435412c02316bd5a43f5733954d8/docs/SIMULATION_LEARNINGS.md)).

**Consequence.** Capable agents appear incompetent; budget is consumed by
recovery loops; behavioral measurements reflect documentation drift.

**Recurrence signals.** Repeated “not found” errors; agent cites a removed
primitive; examples and tool schemas disagree; a rename requires agent prompt
patches after runtime merge.

**Prevention constraint.** Version agent-visible instructions with typed world
tools and verify them through an authentic agent turn.

**Audit probe / fail condition.** Execute the canonical first action using the
same skills/hooks/tool descriptions the resident agent receives. Fail a tool or
schema change if old names remain in active context.

### FM-09 — Small schema/observation defects cause ecology-wide paralysis

**Mechanism.** A bad count, duplicate item, missing quota, ambiguous error, or
schema mismatch is broadcast to every actor, which then synchronizes on the
same mistaken premise.

**Evidence.** AE2 reported 45 artifacts while only 30 were unique. All three
agents spent ten ticks searching for phantom executables and created nothing.
The same learning record notes a cold-start prompt cycle in which everyone
waited for others to create.

**Consequence.** A minor observability bug becomes an ecology-level deadlock and
can be misdiagnosed as model incapacity or economic behavior.

**Recurrence signals.** All agents repeat the same query/error; zero productive
actions despite budget; displayed aggregate cannot be reconciled to item-level
state; cold-start prompts assume pre-existing work.

**Prevention constraint.** Reconcile aggregate views to typed source state;
seed only necessary affordances; include a detector for synchronized no-op or
search loops.

**Audit probe / fail condition.** Corrupt one summary field and run a bounded
agent turn. The system must surface inconsistency or recover without all agents
stalling. Fail if the dashboard/summary disagrees with kernel truth.

### FM-10 — Scarcity or interdependence does not actually bind

**Mechanism.** Agents have ample independent resources, similar capabilities,
self-contained goals, or no profitable reason to exchange.

**Evidence.** AE2's three 300-second discourse-v3 runs used less than one
percent of LLM budget, yielded zero or one cross-agent invocation, and no scrip
movement. Evaluation 07's only valid pair had prescribed
`scarcity_binding=false` and minimal `true`, so the treatment manipulation did
not hold. AE3 needed explicit pre-dispatch scarcity controls and later hard
call caps.

**Consequence.** Absence of coordination says nothing about agent willingness;
the environment never created a need. Conversely, an unequal scarcity
manipulation confounds condition comparisons.

**Recurrence signals.** Budgets end near start; agents can complete goals alone;
capabilities/information are cosmetically rather than operationally different;
conditions bind at different rates.

**Prevention constraint.** Prove scarcity and interdependence from receipts
before interpreting behavior. Use complementary capabilities/information and
an isolated baseline.

**Audit probe / fail condition.** Reconcile affordability at every dispatch and
report binding rate by condition. Invalidate a comparison when the manipulation
does not separate as preregistered or differs unintentionally between cells.

### FM-11 — Plumbing and activity metrics are promoted as thesis evidence

**Mechanism.** Passing actions, transfers, entropy, artifacts, or dashboard
events are treated as proof of strategic adaptation or collective capability.

**Evidence.** AE2 V1 acceptance checked execution, artifacts, transfers,
constraints, escrow, and logging while declaring sufficiency for emergent
collective capability. AE3 Plan 22 produced a valid 14-action run dominated by
nine strategy writes; Plan 23 correctly treated that as below threshold. Plan
19 sign-off explicitly limits its conclusion to one local MVP observation.

**Consequence.** Healthy plumbing becomes an overclaimed scientific result.

**Recurrence signals.** Claims use counts without trace-grounded adaptation;
entropy is called usefulness; self-reads are purchases; fixture activity is
counted as endogenous market use.

**Prevention constraint.** Keep three separate evidence layers: kernel health,
behavioral proxy, and decision-level thesis claim.

**Audit probe / fail condition.** For each conclusion, identify the exact
construct and alternative explanations. Fail promotion when evidence proves
only that a mechanism executed.

### FM-12 — A synchronous provider boundary blocks async control

**Mechanism.** An async loop calls a synchronous provider client, so timeout,
cancellation, monitoring, and parallel control cannot run while the call is
blocked.

**Evidence.** Evaluation 04's first implementation serialized provider latency
inside the async loop; monitor timing extended beyond its intended horizon.
Plan 5 repaired the async scheduling boundary before Evaluation 05.

**Consequence.** Runtime duration and cancellation cease to mean what the
experiment specified; provider latency contaminates ecology timing.

**Recurrence signals.** Event-loop lag tracks provider latency; timeout monitor
runs only after calls finish; apparently parallel agents execute serial calls
for accidental rather than chosen reasons.

**Prevention constraint.** Use the shared async client boundary and explicitly
test monitor responsiveness during a blocked call.

**Audit probe / fail condition.** Inject a delayed provider response and prove
pause/stop/timeout events occur on schedule. Fail before paid behavioral runs if
control latency is coupled to provider latency.

### FM-13 — Provider formatting/reliability failure is counted as agent behavior

**Mechanism.** Truncation, timeout, empty response, malformed tool output, or
provider-specific schema behavior lowers a behavioral metric.

**Evidence.** MiniMax truncation/timeouts reduced Evaluation 04's valid-decision
rate and invalidated the ablation before the minimal condition ran. Evaluation
06 later held out cases and qualified both prompt routes at 16/16 and 15/16
usable actions with zero timeout/truncation/custody failures.

**Consequence.** A provider/instrument defect is interpreted as cognitive or
economic behavior.

**Recurrence signals.** Invalid decisions cluster by provider or output length;
condition conclusions change after parser repair; treatment never starts
because control transport fails.

**Prevention constraint.** Qualify exact model, prompt, schema, transport, and
parser separately on held-out cases before behavioral spend.

**Audit probe / fail condition.** Require a frozen reliability threshold and
named terminal classifications. Block behavioral interpretation when the
instrument is unqualified.

### FM-14 — Trace linkage is mistaken for full evidence custody

**Mechanism.** A trace ID connects records, but raw rendered input, provider
response, tool envelope, normalized decision, or receipt is missing.

**Evidence.** Evaluation 04 linked all 94 paid attempts to shared-client
receipts, yet successful tool-call rows generally omitted the raw tool-call
envelope.

**Consequence.** Auditors can prove identity but not what the model actually
returned or how normalization changed it.

**Recurrence signals.** “All traces matched” is the custody conclusion; only
parsed arguments survive; response and tool payload equality cannot be tested.

**Prevention constraint.** Preserve rendered input, raw provider output/tool
envelope, parsed action, normalized action, result, and terminal receipt under
one stable attempt identity.

**Audit probe / fail condition.** Select a successful and failed attempt and
reconstruct the full chain byte-for-byte. Fail custody if any edge is inferred.

### FM-15 — An assay assumes metadata outside the public contract

**Mechanism.** The verifier checks an internal or optional field rather than
the exact public readback contract that retains the evidence fact.

**Evidence.** Evaluation 05 retained byte-for-byte response/tool payloads for
all successful calls but classified all 32 as custody failures because public
records lacked the SQLite-only `content_persistence` field. The frozen verdict
remained `not_qualified`; Evaluation 06 added real public-readback positive,
metadata-only, and corruption controls and qualified.

**Consequence.** A false negative wastes paid evidence and tempts post-hoc
threshold changes.

**Recurrence signals.** Verifier imports internal storage; optional metadata is
treated as the evidence fact; exact payload equality passes while verdict
fails.

**Prevention constraint.** Freeze and test the public reader before spend.
Separate payload custody from auxiliary metadata.

**Audit probe / fail condition.** Run untouched, metadata-only, and corrupted
records through the same public API used after the run. Stop before dispatch if
the controls do not classify correctly.

### FM-16 — Paid-worker lifetime or cwd inherits an interactive/worktree lifecycle

**Mechanism.** A long-lived worker belongs to a chat tool call or starts from a
feature worktree that is later removed.

**Evidence.** Evaluation 07 ended during pair 06 after 189 settled attempts
without its finalizer; the external termination cause was not retained. Plan
21 launched a paused worker from a worktree; after merge/removal, `Path.cwd()`
failed inside shared-client lifecycle logging before dispatch.

**Consequence.** Runs become terminal partial evidence, or local lifecycle
failure is mistaken for provider/agent behavior.

**Recurrence signals.** Worker parent is an interactive session; cwd contains
`worktrees/`; status disappears with the tool process; finalizer is the only
owner of terminal evidence.

**Prevention constraint.** Launch supervised workers from the durable run
directory with an explicit project identity. Worker survival and evidence
finalization must be independent of the development checkout and chat session.

**Audit probe / fail condition.** Remove the launching worktree and disconnect
the operator while paused/running. The worker must continue or stop with a
truthful terminal receipt, never substitute behavior.

### FM-17 — Provider settlement, decision, and custody are not atomic

**Mechanism.** A provider call settles in one record while decision parsing,
world application, and custody checkpoint commit separately.

**Evidence.** Evaluation 07 `pair_02/prescribed` retained 16 settled attempt
events but only 15 loop-decision/custody records. A cancelled call crossed the
stop boundary. Evaluation 07 therefore had 189 settlements and 188 complete
attempt records. Plans 10 and 14 later introduced recoverable checkpoints and
atomic attempt phases.

**Consequence.** Recovery may repeat a paid call, lose a decision, double-apply
an action, or promote ambiguous state.

**Recurrence signals.** Counts differ among provider receipts, syscall events,
loop decisions, world actions, and checkpoints; restart code cannot decide
whether to redispatch.

**Prevention constraint.** One recoverable attempt state machine must own
reservation, dispatch ambiguity, settlement, normalization, application, and
commit. Ambiguity fails closed without redispatch.

**Audit probe / fail condition.** Inject termination between every persistence
boundary and restart. Require exactly-once dispatch and application or a
terminal invalid receipt.

### FM-18 — A fallback action masquerades as authentic agent behavior

**Mechanism.** On LLM, schema, gate, or action failure, the runtime executes a
deterministic local action and records the mechanical result as a successful
agent decision.

**Evidence.** The deleted-cwd Plan 21 incident produced 14 local
`query_kernel` fallbacks, zero shared-client receipts, and displayed them as 14
successes. Plan 22 repaired authentic runs with
`fail_closed_no_substitute` and made historical substitutes visibly untrusted.
The current generated loop still retains configurable fallback behavior for
provider-free/legacy cases.

**Consequence.** A completely failed LLM path can look like a functioning
ecology and contaminate every downstream metric.

**Recurrence signals.** `success=true` with `fallback_used=true`; provider
receipts fewer than agent decisions; local action success substitutes for model
selection; error rates fall when fallback rises.

**Prevention constraint.** Authentic runs must stop invalid on the first
transport, schema, gate, or selected-action failure. Substitute decisions may
exist only in explicitly non-authentic fixtures and must be excluded from
behavioral evidence.

**Audit probe / fail condition.** Break cwd/provider/schema/action in turn.
Require zero committed substitutes, visible original error, and terminal
invalid custody.

### FM-19 — Conditions receive unequal call exposure because scarcity and prompts interact

**Mechanism.** Different prompts consume different tokens, so a shared budget
causes one condition to stop earlier or dispatch past the intended horizon.

**Evidence.** Evaluation 12 stopped prescribed at 14/16 before minimal began.
Evaluation 14 then had prescribed stop correctly after 14 plus a pre-dispatch
scarcity boundary, while the cheaper minimal condition dispatched a 15th call;
the pair was invalid. Evaluation 15 added an independent hard call cap.

**Consequence.** Behavioral differences are confounded with unequal exposure;
budget exhaustion cannot substitute for a call-count control.

**Recurrence signals.** Attempt counts differ by condition; token use differs
systematically by prompt; the stopping rule depends only on budget.

**Prevention constraint.** Enforce both economic budget and independent global
and per-principal dispatch ceilings. Match or explicitly model exposure.

**Audit probe / fail condition.** Run provider-free cheap/expensive response
fixtures. Both must stop at the frozen call horizon; invalidate any pair with
unequal dispatch count.

### FM-20 — Provider billing semantics make simulated economic scarcity non-binding

**Mechanism.** Subscription routes report zero marginal provider USD, while
the ecology treats provider cost as the scarce internal budget.

**Evidence.** AE3's Luna runs reported subscription-included USD cost of zero.
AE3 therefore added `subscription_budget_charge_mode=estimated` and retained
separate internal estimated charges.

**Consequence.** Agents can receive effectively unlimited cognition, or a
synthetic charge can be mistaken for real provider expenditure.

**Recurrence signals.** Provider cost remains zero while internal budget never
moves; reports combine real USD and simulated units; changing billing route
changes behavior without an economic-config revision.

**Prevention constraint.** Keep real provider cost, internal simulation charge,
and call/token quotas as separately named units. Calibrate the internal charge
for the intended manipulation.

**Audit probe / fail condition.** Reconcile provider receipt billing mode to
ledger movement. Fail scarcity claims if the constrained unit did not bind or
if real and pseudo costs are conflated.

### FM-21 — Missing observation memory produces repetitive or falsely attributed adaptation

**Mechanism.** A read succeeds economically, but the purchased target/content
is absent from the next agent context.

**Evidence.** Plan 23 run 1 produced repeated paid reads and apparent later
adaptation, but state retained only action type and success. Because the buyer
did not receive purchased content in its next prompt, adaptation could not be
attributed to the read. Run 2 added bounded purchased-content memory and
produced the intended chain, although that run then failed exposure; run 3
passed the frozen technical rubric.

**Consequence.** Agents repeat purchases, and analysts infer learning from
information the model never saw.

**Recurrence signals.** Same artifact bought repeatedly; read dominance;
decision explanation references no observed content; event log shows success
but rendered next prompt lacks the payload.

**Prevention constraint.** A successful observation must have a bounded,
private, auditable path into the agent's next context. Attribution requires
prompt custody.

**Audit probe / fail condition.** Trace one purchase from authorization and
payment through returned content into the next rendered prompt and subsequent
decision. Reject adaptation claims if the chain breaks.

### FM-22 — Agent/runtime policy complexity reconcentrates in a generated monolith

**Mechanism.** A clean rewrite remains small overall but accumulates world
setup, cognition, memory, parsing, gates, fallbacks, provider profiles, and
accounting in one file and one generated code string.

**Evidence.** Current AE3 `world.py` is 2,867 lines. Its generated loop spans
lines 950–1778 and owns most of the actor lifecycle. The file has grown from
2,125 lines at the 2026-08-11 lineage review. This is a structural watch item,
not proof that line count caused a current failure.

**Consequence.** A future change can couple agent configuration to kernel
authority and repeat AE2's restart pressure.

**Recurrence signals.** World-file growth; changes to prompts and economic
settlement in the same diff; generated source instead of typed modules; tests
must construct the entire world to exercise agent policy.

**Prevention constraint.** In the simplified version, the kernel exposes typed
world tools and settlement; agent runtime configuration lives outside it.
Extract only along demonstrated ownership seams, not line-count aesthetics.

**Audit probe / fail condition.** Quarterly or at major capability changes,
map file/module ownership to invariants. Trigger redesign when one module owns
both agent cognition and economic authority or blocks a vertical change.

### FM-23 — Global serialization silently defines ecology timing

**Mechanism.** Multiple autonomous loops exist, but a global lock serializes
each world execution, including awaited model calls.

**Evidence.** AE3 `SimulationRunner` uses one `_world_execution_lock` around
`execute_action_data_async`. This may be intentional deterministic semantics,
but no retained incident proves its behavioral effect; classify it as an
inference/watch item.

**Consequence.** Provider latency may determine turn order; apparent
competition or response time may be scheduler artifact; “parallel agents” is
an overclaim.

**Recurrence signals.** One slow call blocks every principal; action order
tracks latency; documentation says concurrent while traces are globally serial.

**Prevention constraint.** Declare scheduling semantics. If model thinking is
outside the serialized kernel boundary, settle world mutations with explicit
optimistic/pessimistic rules; if fully serial, call it serial.

**Audit probe / fail condition.** Delay one agent and inspect whether unrelated
agents progress. Fail any concurrency or timing claim inconsistent with the
observed scheduler.

### FM-24 — Process and presentation grow around an unresolved experiment

**Mechanism.** Plans, governance, dashboards, documentation graphs, and review
machinery expand while the key behavioral question remains inconclusive.

**Evidence.** AE2 accumulated extensive governance/dashboard/documentation
surfaces during architecture churn. AE3 deliberately removed those surfaces,
then re-added meta-process tooling and a bounded dashboard while its decisive
prescription ablation remained unresolved. AE3's current roadmap appropriately
guards against a second dashboard, configuration-panel zoo, and infrastructure
without a user question.

**Consequence.** Process creates the feeling of rigor without resolving the
experiment; maintenance competes with direct learning.

**Recurrence signals.** Two consecutive process/UI increments without stronger
authentic evidence; new gates protect no reproduced failure; multiple canonical
surfaces; plans outnumber observed verticals.

**Prevention constraint.** Every control names the incident it protects; every
UI serves the canonical operator journey; the next empirical uncertainty owns
the critical path.

**Audit probe / fail condition.** At each roadmap review, ask which current
failure or user-visible result a new process surface changes. Defer it when the
answer is only completeness, generality, or future scale.

## Proposed recurring audit contract

The following is the handoff surface for Company Planning/AES adoption. The
owning methodology should import the questions and failure IDs, not copy this
project's implementation details.

| Audit moment | Required evidence | Failure IDs | Block/response |
|---|---|---|---|
| Project charter / bounded design | Claimed agent boundary, kernel boundary, canonical example, non-claims, real uncertainty | 01, 02, 05, 07, 11, 24 | Block design if “agent,” “emergence,” or “ecology” has no operational test. |
| Architecture adoption | One owner per invariant; existing capability owner; consumer-level adoption proof; deletion/non-goals | 02, 05, 06, 07, 22, 23 | Reject duplicate agent/runtime or world-authority paths. |
| Configuration/prompt review | Diff of roles, objectives, seed artifacts, skills, hooks, permissions, memory, gates, fallbacks | 01, 08, 10, 21 | Mark prescribed mechanisms; require ablation for behavioral claims. |
| Pre-spend instrument qualification | Exact route, model, prompt, schema, public readback controls, async responsiveness, call/budget caps | 12–15, 19, 20 | No behavioral dispatch until controls pass. |
| Run-start audit | Clean pinned source/dependency revisions, durable cwd/supervisor, paused zero-dispatch state, immutable config and schedule | 04, 16, 19 | Stop before dispatch on drift or interactive-only custody. |
| Per-run validity audit | Receipt/attempt/decision/action count reconciliation, exact custody, scarcity, origin attribution, no substitutes | 01, 10, 13, 14, 17–20 | Invalidate the run; preserve it; do not repair interpretation post hoc. |
| Behavioral interpretation | Trace-grounded adaptation, isolated alternative explanations, plumbing/proxy/thesis claim separation | 01, 10, 11, 21 | Narrow the claim or require a fresh evaluation. |
| Independent decision sign-off | Frozen rubric, representativeness, generalization boundary, no same-session self-signoff | 04, 11, 13–21 | No kill/continue/promotion decision from invalid evidence. |
| Periodic architecture/roadmap audit | Module ownership map, current consumers, obsolete paths, process/UI growth versus authentic outcomes | 05–07, 22–24 | Delete/defer bounded accretion or open a named redesign decision. |

### Minimum machine-checkable run invariants

For every authentic run, the audit should be able to compute rather than infer:

1. requested, resolved, and executed model/transport/billing identity;
2. provider dispatch count, settled count, normalized decision count, applied
   action count, and committed attempt count;
3. exact equality or content hashes across caller result, public readback, raw
   tool/structured payload, and checkpoint;
4. retry, repair, fallback-model, gate-fallback, recovery-fallback, forced
   exploration, and substitute counts;
5. per-principal call/token/internal-budget exposure and the exact stopping
   boundary;
6. whether the claimed scarce resource actually bound;
7. whether every observation used for adaptation appeared in the next rendered
   agent context; and
8. source, dependency, config, prompt, scenario, seed, and evidence-bundle
   identities.

Any count mismatch is a named invalidity, not a warning. Any substitute action
is invalid behavioral evidence. Missing generalization evidence narrows the
claim; it does not invalidate a correctly bounded local observation.

## Design constraints for the simplified Agent Ecology

These are the strongest lineage-derived constraints, independent of the final
rewrite/fork decision:

1. **Use real resident/headless agents.** Configure Codex or Claude through
   `llm_client`; do not rebuild their ordinary memory, planning, skills, hooks,
   permission, and tool lifecycle inside the ecology.
2. **Keep the kernel narrow.** It owns typed world state, economic rules,
   authorization, atomic settlement, scheduling semantics, and durable receipts.
3. **Make agent configuration data, not kernel code.** Model, instructions,
   skills, hooks, tool grants, resource endowment, and visibility are versioned
   contracts with strict unknown-key rejection.
4. **No substitute behavior in authentic runs.** Fail visibly and preserve the
   original boundary error.
5. **Qualify the instrument before studying behavior.** Provider reliability,
   public readback, custody, recovery, and exposure controls are prerequisites,
   not behavioral metrics.
6. **Prove the manipulation.** Scarcity, heterogeneity, and interdependence must
   be visible in receipts before a coordination result is interpreted.
7. **Keep claims layered.** A functioning kernel, an interesting local trace,
   and a general emergence claim require different evidence.
8. **One canonical example and one evidence lineage.** Reopen it from a fresh
   process; use it as the stable regression and comprehension surface.
9. **Controls must pay rent.** Add a gate, process, UI, or abstraction only for
   a reproduced failure, protected shared-state boundary, or next authentic
   outcome.

## Source map

### Cross-line synthesis

- [Lineage and Restarts](LINEAGE_AND_RESTARTS.md)
- [AE3 Rewrite Scope (retired, pinned)](https://github.com/BrianMills2718/agent_ecology3/blob/28574ed2a65870e8657c5c16e16b7fdd872cc71e/docs/REWRITE_SCOPE.md)
- [AE3 Removal Sequence (retired, pinned)](https://github.com/BrianMills2718/agent_ecology3/blob/28574ed2a65870e8657c5c16e16b7fdd872cc71e/docs/REMOVAL_SEQUENCE.md)
- [AE3 MVP Roadmap](MVP_ROADMAP.md)

### AE1 primary sources

- [`world_v1.py`](https://github.com/BrianMills2718/agent_ecology/blob/720920732373292d1353be9a1f8066016b6f5aa8/world_v1.py)
- [`world_v2.py`](https://github.com/BrianMills2718/agent_ecology/blob/720920732373292d1353be9a1f8066016b6f5aa8/world_v2.py)
- [`sweep.py`](https://github.com/BrianMills2718/agent_ecology/blob/720920732373292d1353be9a1f8066016b6f5aa8/sweep.py)

### AE2 primary sources

- [Simulation Learnings](https://github.com/BrianMills2718/agent_ecology2/blob/33bbb6de0142435412c02316bd5a43f5733954d8/docs/SIMULATION_LEARNINGS.md)
- [V1 Acceptance](https://github.com/BrianMills2718/agent_ecology2/blob/33bbb6de0142435412c02316bd5a43f5733954d8/docs/V1_ACCEPTANCE.md)
- [Plan 298: Config-Driven Genesis](https://github.com/BrianMills2718/agent_ecology2/blob/33bbb6de0142435412c02316bd5a43f5733954d8/docs/plans/298_config_driven_genesis.md)
- [Plan 299: Eliminate Legacy Agents](https://github.com/BrianMills2718/agent_ecology2/blob/33bbb6de0142435412c02316bd5a43f5733954d8/docs/plans/299_eliminate_legacy_agents.md)

### AE3 incident and repair sources

- [Evaluation 04: Prescription Ablation](evaluations/04_prescription_ablation.md)
- [Evaluation 05: Provider/Tool Qualification](evaluations/05_provider_tool_qualification.md)
- [Evaluation 06: Public-Readback Qualification](evaluations/06_public_readback_qualification.md)
- [Evaluation 07: Behavioral Comparison](evaluations/07_behavioral_comparison.md)
- [Evaluation 12: Behavioral Feasibility](evaluations/12_luna_behavioral_feasibility.md)
- [Evaluation 14: Feasibility Repair](evaluations/14_luna_behavioral_feasibility.md)
- [Evaluation 15: Hard Call Cap](evaluations/15_luna_hard_call_cap.md)
- [Plan 10: Recoverable Luna Gate](plans/10_luna_medium_recovery_gate.md)
- [Plan 22: Fail-Loud Authentic Runs](plans/22_fail_loud_authentic_runs.md)
- [Plan 23: Emergent Interaction](plans/23_emergent_interaction.md)
- [Plan 19 Sign-Off](evaluations/19_live_economic_mvp_signoff.md)
