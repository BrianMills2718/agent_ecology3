# Agent Ecology Repository Lineage and Restart Lessons

**Status:** Current orientation
**Reviewed:** 2026-08-11 (standing rebuild constraints added 2026-10-05)
**Reviewed revisions:**

- `agent_ecology`: `720920732373292d1353be9a1f8066016b6f5aa8`
- `agent_ecology2`: `33bbb6de0142435412c02316bd5a43f5733954d8`
- `agent_ecology3`: `80c34e1a7e5636e9b8a3b4295c2f6ce7f13d159c`

This is the short, current entry point for understanding why three Agent
Ecology repositories exist. It consolidates evidence; it does not replace the
detailed removal records, simulation notes, or Project Meta lifecycle authority.
The detailed prevention and recurring-audit companion is the
[Agent Ecology Failure-Mode Dossier](FAILURE_MODE_DOSSIER.md).

## Lifecycle Boundary

Repository numbering is not lifecycle authority. At the review date, Project
Meta records:

- `agent_ecology` as archived and superseded by `agent_ecology2`;
- `agent_ecology2` as active; and
- `agent_ecology3` as active, with no formal supersession edge to or from AE2.

Therefore AE3 is a clean rebuild **of ideas and selected behavior**, but it is
not yet the formally declared replacement for every AE2 capability. Changing
that status requires an explicit Project Meta decision.

## Evidence Labels

- **Documented decision** — stated by an accepted scope/decision record.
- **Observed** — directly supported by source, history, a test, or an execution.
- **Inferred** — the best explanation supported by observations, but not found
  as an explicit historical decision. Inferences must not be rewritten as fact.

## What Each Repository Is

Snapshot counts below use tracked files at the reviewed revisions. Line counts
are physical Python lines, not complexity or quality scores.

| Repository | Actual scope | Snapshot | Best use now |
|---|---|---:|---|
| `agent_ecology` (AE1) | A deterministic, tick-based heuristic simulation of tool choice, congestion, private memory, and reciprocity. It has no LLM agents, contract economy, durable runtime, package boundary, or tests. | 1 commit; 5 tracked files; 1,936 Python lines; 0 tests; 0 Markdown docs. | Archived conceptual seed and small mechanism counterexample harness. |
| `agent_ecology2` (AE2) | A broad LLM-agent simulation substrate: artifacts, contracts, escrow, resource accounting, continuous loops, checkpoints, dashboards, extensive governance, and several generations of agent cognition. | 1,211 commits; 708 tracked files; 25,864 source lines; 33,916 test lines; 44,417 Markdown lines. | Full capability/reference line and source of historical behavioral evidence. It remains active in Project Meta. |
| `agent_ecology3` (AE3) | A clean-room kernel and experiment line centered on fewer authority paths, strict configuration, JSONL events, autonomous artifact loops, a lean API, and repeated scarcity/emergence analysis. | 41 commits; 151 tracked files; 8,764 source lines; 1,959 test lines; 10,403 Markdown lines. | Preferred line for the next falsifiable emergence experiment, subject to the evidence cautions below. It also remains active in Project Meta. |

The names “v1” and “v2” inside AE1 and agent generations such as
`discourse_v3` inside AE2 are local experiment versions. They are not the same
thing as the AE1/AE2/AE3 repository lineage.

## Transition 1: AE1 to AE2

### What is authoritative

Project Meta says AE2 supersedes AE1. No repository-local decision record was
found that explains the restart itself.

### What the evidence shows

**Observed:** AE1 is four standalone Python programs. Its policies are coded
directly into the simulation: agents choose tools using fixed probabilities and
observed acceptance, while the AE1 “v2” adds an explicit grudge/reciprocity
rule. See the immutable
[`world_v1.py`](https://github.com/BrianMills2718/agent_ecology/blob/720920732373292d1353be9a1f8066016b6f5aa8/world_v1.py),
[`world_v2.py`](https://github.com/BrianMills2718/agent_ecology/blob/720920732373292d1353be9a1f8066016b6f5aa8/world_v2.py),
and [`sweep.py`](https://github.com/BrianMills2718/agent_ecology/blob/720920732373292d1353be9a1f8066016b6f5aa8/sweep.py).

**Observed execution:** both world scripts run. In the fixed-seed comparison
built into `world_v2.py`, adding reciprocity reduced acceptance from about
0.510 to 0.393 and mean utility from about 130.5 to 105.8, while utility Gini
rose from about 0.081 to 0.208. The rule successfully creates feuds, but that
is a consequence of a prescribed tit-for-tat mechanism, not evidence that LLM
agents discovered reciprocity.

**Inferred restart reason:** AE1 reached the boundary of a useful toy model.
The project needed real LLM cognition, explicit resources and contracts,
persistence, configuration, observability, and tests. AE2 began as a much
larger substrate rather than an incremental refactor of the four-file model.

### Failure modes learned from AE1

1. **Mechanism output can be mistaken for emergence.** If a reciprocity rule is
   installed by the designer, the resulting grudge network validates the rule's
   dynamics, not spontaneous institutional formation.
2. **Copy-forward versions duplicate the whole authority surface.** AE1's
   `world_v1.py` and `world_v2.py` repeat most of the world instead of isolating
   one intervention, making later comparison and maintenance harder.
3. **A runnable demo is not a durable experiment.** There are no tests,
   environment declaration, saved receipts, or prose decision record.

AE1 should remain archived. Port a tiny mechanism or observation only when a
current experiment needs it; do not restart from its codebase.

## Transition 2: AE2 to AE3

### Documented restart reason

AE3's [rewrite scope][rewrite-scope] and
[full-context handoff][full-context] state that AE3 was a clean
rebuild because AE2 had accumulated code smell and architecture sprawl. Six
removals, approved by Brian on 2026-02-20, made that diagnosis concrete:

1. runtime-adjacent governance/process scaffolding;
2. compatibility shims and one-off dispatch paths;
3. duplicated authority boundaries;
4. dashboard frontend sprawl;
5. dormant subsystems in the default boot path; and
6. broad backward-config compatibility.

The [removal sequence][removal-sequence] was the index; the six removal
records held the detailed AE2 code observations. Those planning records were
retired from the working tree on 2026-10-05 after their binding content was
promoted below; the links here open them at the last commit that contained
them.

### Standing constraints from the rebuild

These still bind AE3 unless a later ADR or the active plan changes them. Each
was checked against the code on 2026-10-05.

1. **No process tooling in the runtime path** (Removal 01). Plan, worktree,
   and governance helpers live under `scripts/meta/`; no module under
   `src/agent_ecology3/` imports them.
2. **No compatibility shims** (Removal 02). One typed config, one action
   vocabulary, no deprecated aliases in the core parser, and no silent
   provider-guess fallback in accounting paths. (Normalizing common LLM
   output variants into the canonical action is input parsing, not a shim.)
3. **One path per concern** (Removal 03). Resources go through `Ledger` and
   `RateTracker`; invocation through the executor/action path; permissions
   through one contract engine; LLM accounting through the shared
   `llm_client`, with the world only reconciling budget and rate usage.
4. **One bounded dashboard** (Removal 04). A single FastAPI dashboard
   (`src/agent_ecology3/dashboard/`, inventoried in `ui/registry.yaml`); every
   displayed metric maps to one canonical event or state source; add a view
   only for a concrete operator question. The roadmap's YAGNI list repeats
   this ("no second dashboard").
5. **Small default boot path** (Removal 05). External capabilities, the
   secondary invocation registry, and the rich resource-metrics provider stay
   out of default boot. *Partly superseded:* Removal 05 also kept the
   task-based mint out of the core path; Plan 24 M2 deliberately added an
   outside-scored `task_bounty` mint mode (`mint.mode` in
   `src/agent_ecology3/config.py`) for the trading-vs-solo comparison.
6. **Strict config schema** (Removal 06). Every config model rejects unknown
   keys (`extra="forbid"` in `src/agent_ecology3/config.py`); AE2-era keys
   fail validation instead of being aliased.

The operator principles recorded in the full-context handoff also remain
binding design constraints:

- contracts govern access rights; "owner" is not the rights model;
- scarce resources are allocated first and then reallocated by contracts or
  trade, and kernel fairness for its own sake is not a goal;
- do not script the target behavior and call it emergence;
- keep the architecture simple until evidence demands more; and
- prefer measured accounting over approximation when the effort is similar
  (see [Resource Accounting](RESOURCE_ACCOUNTING.md)).

### Observed support for that decision

1. **The substrate grew faster than one stable vertical.** AE2 has 31 modules
   under `src/world` alone. Resource control, invocation, kernel queries,
   permissions, and LLM accounting each acquired overlapping wrappers or
   stores, as catalogued in
   [Removal 03][removal-03].
2. **Large deletions were needed while AE2 was still evolving.** Its history
   records removal of roughly 29,000 lines of a legacy agent system, roughly
   6,800 lines of a dead dashboard generation, and another roughly 4,200 lines
   of dead code shortly before the AE3 rebuild. That is direct evidence of
   converging after speculative breadth, not merely a stylistic objection.
3. **Stale guidance changed agent behavior.** AE2's
   [`SIMULATION_LEARNINGS.md`](https://github.com/BrianMills2718/agent_ecology2/blob/33bbb6de0142435412c02316bd5a43f5733954d8/docs/SIMULATION_LEARNINGS.md)
   records an agent repeatedly reading a handbook that still referenced a
   removed `genesis_ledger`, and a separate duplicate artifact-count bug that
   left all three agents searching instead of creating.
4. **Working plumbing did not establish the thesis.** AE2's three 300-second
   `discourse_v3` smoke runs produced zero or one cross-agent invocation per
   run and no scrip movement. Its diagnosis was cognitively similar agents,
   self-contained goals, non-binding scarcity, and prescribed cooperation.
   The “v3” here is an AE2 agent generation, not the AE3 repository.
5. **The acceptance gate was structurally weaker than the project claim.**
   AE2's
   [`V1_ACCEPTANCE.md`](https://github.com/BrianMills2718/agent_ecology2/blob/33bbb6de0142435412c02316bd5a43f5733954d8/docs/V1_ACCEPTANCE.md)
   says V1 is sufficient to demonstrate emergent collective capability, but
   its checks establish multi-agent execution, artifact operations, transfers,
   constraints, escrow, and logging. Those are necessary plumbing checks; none
   distinguishes discovered cooperation from scripted or absent cooperation.

### What did not fail

AE2 is not simply broken software. In this review, its suite passed 1,687 tests
with 14 skipped once the workspace's shared `llm_client` checkout was installed.
The restart addressed architecture, experimental validity, and iteration cost;
it was not caused by an inability to execute basic kernel behavior. AE2 also
received maintained changes after AE3 began, which is consistent with Project
Meta keeping both lines active.

## Recurring Failure Modes to Prevent

| Failure mode | How it appeared | Guardrail for current work |
|---|---|---|
| Prescribed behavior presented as emergence | AE1 hard-coded reciprocity; AE2 smoke agents had explicit cross-agent tasks; AE3 has role playbooks and deterministic fallback actions. | Use ablations with intervention off and attribute every decision origin. Treat activity as emergence only when it survives the non-prescriptive condition. |
| Non-binding scarcity | AE2 smoke runs used less than 1% of LLM budget and produced no exchange pressure. | Establish from traces that the constrained resource binds before interpreting coordination outcomes. |
| Cognitively identical agents with self-contained goals | AE2's agents had cosmetic specialization and no real need for one another. | Create heterogeneous capabilities or information, then test whether exchange improves outcomes over isolated baselines. |
| Plumbing metrics used as thesis evidence | Transfers, action entropy, and passing acceptance tests can all occur without strategic adaptation. | Keep kernel health, behavioral proxies, and thesis-level evidence as three separate claims. |
| Duplicated authority | AE2 split resources, invocation, queries, permissions, and accounting across parallel paths. | One owner per invariant and one integration check proving the intended consumer used it. |
| Compatibility and dormant-path accumulation | AE2 retained old config keys, dispatch variants, checkpoints, dashboards, and disabled subsystems. | Reject compatibility by default in AE3; add an adapter or extension only for a named current caller or experiment. |
| Stale context drives runtime failure | AE2 agents acted on obsolete handbook concepts; later documentation repeatedly repaired renamed or removed primitives. | Version agent-visible guidance with the runtime contract and exercise it in the same vertical check. |
| Evidence is not reopenable | AE1 saved no run receipts; AE3's README/handoff cites logs and suite summaries that are not tracked in a clean clone. | Preserve a compact, immutable evidence bundle or a durable experiment-registry reference for every decision-driving run. |
| Wall-clock control assumes a responsive event loop | AE3 Evaluation 04 called a synchronous provider client from its async loop; serial latency and timeouts delayed the monitor beyond its original horizon. | Use an async-safe provider boundary and prove that cancellation/timeout monitoring remains responsive before behavioral runs. |
| Provider formatting failure is counted as behavior | MiniMax truncation and timeout errors lowered AE3's LLM-valid-decision rate enough to invalidate the first ablation before treatment. | Qualify model/prompt/tool-schema reliability separately, then freeze the behavioral evaluation without changing its thresholds midstream. |
| Trace IDs mistaken for complete custody | Evaluation 04 linked every AE3 attempt to a shared-client receipt, but successful tool-call rows generally omitted the raw tool-call envelope. | Preserve rendered input, raw provider output/tool envelope, normalized decision, and receipt together; verify the chain before interpretation. |
| Auxiliary metadata mistaken for the custody fact | Evaluation 05's public call records contained byte-for-byte matching response/tool payloads, but its classifier rejected all attempts because that API did not expose the SQLite `content_persistence` column. | Test the exact public readback shape before spend and establish custody from exact caller/readback equality. Treat missing optional metadata as an assay defect, not as proof that retained payloads differ. |
| Paid evaluation lifetime tied to an interactive agent session | Evaluation 07's worker ended without running its finalizer after 189 settled attempts. The exact external termination cause was not retained, and the frozen no-rerun rule made the partial cell terminal. | Run paid assays under a durable supervisor independent of the chat/tool session. Persist world, scheduler, RNG, attempt, and cost state frequently enough that recovery never repeats a provider attempt. |
| Settled attempt and custody checkpoint are not atomic | Evaluation 07 `pair_02/prescribed` retained 16 settled attempt events but only 15 loop decisions/custody records; the final `llm call cancelled` event crossed the stopping boundary without a linked attempt capture. | Commit settlement, decision/failure classification, and custody as one recoverable transaction, and exercise cancellation between each persistence boundary before spend. |
| Durable worker inherits a disposable worktree cwd | The Plan 21 worker was launched paused from a feature worktree, which was removed after merge. On Resume, `Path.cwd()` failed inside shared-client lifecycle logging before Codex dispatch; AE3 committed 14 local fallback actions as successes. | Launch long-lived workers from their durable run directory, fail invalid on the first authentic-boundary error, and show substitute provenance as untrusted. |
| Process grows around the experiment | AE2 accumulated extensive plan, governance, dashboard, and documentation surfaces; AE3 later re-added meta-process tooling outside runtime. | Keep process outside runtime and require each new control to protect a reproduced failure or current shared-state boundary. |

## Current AE3 Watch Items

These are observed risks, not reasons to restart AE3 now.

1. **Complexity is concentrating again.** AE3 is much smaller overall, but
   `src/agent_ecology3/world/world.py` is 2,125 lines at the reviewed revision.
   It is already the largest AE3 core file and contains world setup, cognition
   templates, loop policy, and LLM accounting. Split it only when a current
   change demonstrates a second authority or blocks a vertical experiment;
   do not launch a cleanup rewrite on line count alone.
2. **The emergence confound is explicit but still present.** Hard-coded role
   profiles, objective cycles, action gating, auto-pricing, and fallback actions
   can create the behavior being measured. Forced exploration now defaults to
   `off`, and AE3 records decision-origin metrics, which are good safeguards.
   Evaluation 04 added a minimal-cognition switch, but its first frozen assay
   stopped before treatment after a second invalid paid run. Evaluation 05's
   provider/tool qualification descriptively produced usable actions in 16/16
   prescribed and 15/16 minimal calls, but its frozen classifier returned
   `not_qualified` because of the readback-metadata defect. Evaluation 06 then
   qualified the held-out provider/prompt/tool instrument with independent
   signoff. Evaluation 07 attempted the required behavioral comparison, but
   only one of five completed pairs was valid, no included run demonstrated
   binding scarcity, and the worker ended during the sixth pair. The comparison
   therefore remains unresolved, now with terminal partial evidence rather than
   an unexecuted design.
3. **Historical empirical claims are not self-contained in Git.** The README
   and the retired [full-context handoff][full-context] name run IDs and
   summary files, but a clean
   clone contains no tracked logs or summary JSON. Treat those claims as a
   historical handoff until their registry records or immutable evidence are
   reopened.
4. **Clean-clone dependencies are asymmetric.** AE3 documents its
   `llm_client` path fallback and Project Meta declares the dependency. AE2 now
   imports `llm_client`, but its requirements and Project Meta record do not
   declare that dependency; its clean-clone suite initially failed collection
   for that reason during this review.
5. **Coordination configuration has drifted.** AE3 enables claims/worktrees in
   `meta-process.yaml` but does not expose the current sanctioned `make
   worktree`, `make worktree-list`, and `make worktree-remove` entrypoints. Its
   Makefile also defines several workflow targets twice, so `make pr-ready`
   emits recipe-override warnings. This does not affect simulation semantics,
   but it can recreate process ambiguity during parallel work.

## Verification Snapshot

The review intentionally separates code health from thesis evidence:

- AE1: both standalone world scripts executed successfully with Python 3.12.
- AE2: `1,687 passed, 14 skipped` in 37.79 seconds after installing the
  workspace `llm_client` revision `bc2cce248655`; without that undeclared
  dependency, collection failed in seven modules.
- AE3: `51 passed` in 1.79 seconds in an isolated environment.
- No paid LLM run was made during the original repository review. The later
  Evaluation 04 implementation passed `57` tests and spent USD 0.0744073 on a
  preregistered assay that terminated **inconclusive**. Its tracked evidence
  bundle preserves the raw AE3 events, matrices, inputs, hashes, and trace
  audit; the minimal treatment was not run.
- Plan #5 then passed 71 repository tests and repaired AE3's async scheduling
  boundary. Evaluation 05 spent USD 0.0359061 on 32 serial calls with exact
  trace/tool custody, but its immutable runner verdict is **not qualified** due
  to the classifier/readback metadata mismatch documented above. It was not
  rerun and no behavioral evaluation followed.
- Evaluation 06 used a new held-out state and real zero-spend public-readback
  controls before making 32 new calls. It qualified both prompt routes at the
  frozen reliability threshold for USD 0.03988458 and received independent
  adversarial signoff. This repairs the instrument prerequisite; it is not the
  missing behavioral comparison.
- Evaluation 07 then made 189 settled calls for USD 0.23998692 before its paid
  worker ended during `pair_06/prescribed`. Five pairs completed, only
  `pair_03` was valid, no included run bound scarcity, and one earlier cancelled
  attempt exposed a 16-event/15-custody split. The manifest and interruption
  receipt verify the terminal partial bundle, but exact result reproduction is
  intentionally unavailable.

## Advice and Next Decision

Use AE3 for the next experiment whose purpose is to learn whether strategic
coordination emerges. Use AE2 as a capability quarry, behavioral evidence
archive, and regression reference. Keep AE1 frozen.

Do **not** declare AE3 the sole successor yet. First require one stable,
reopenable, fully traced experiment that:

1. makes scarcity demonstrably binding;
2. compares a minimally prescriptive condition with the current role/prompt
   condition on matched seeds;
3. measures downstream reuse or net utility, not activity alone;
4. attributes every counted outcome to LLM choice, policy intervention, or
   deterministic recovery; and
5. preserves the configuration, prompt, model, raw events, summary, and code
   revision behind the readout.

Evaluation 04 was the first attempt to meet this bar. It stopped correctly
rather than relaxing its validity rule, and it exposed two prerequisites for a
fresh evaluation: an async-safe provider boundary and full raw tool-call
custody. Treat those as repairs to the experimental instrument, not as a reason
for another repository rewrite.

Plan #5 implemented both repairs. Evaluation 05 then showed that exact payload
custody alone is not enough if the decision classifier assumes fields outside
the public readback contract. The preserved data is encouraging but does not
replace its frozen verdict. Any further qualification needs a new
preregistration; do not recycle Evaluation 05 as a passing assay.

Evaluation 06 supplied that new preregistration and passed its independently
verified instrument gate. Evaluation 07 used that boundary once, but terminated
inconclusive/invalid after four of five completed pairs failed validity, the
scarcity manipulation failed in the sole included pair, and the worker ended
mid-cell. Its partial observations do not answer the behavioral question and
must not be promoted or rerun. If the question remains worth the spend, the
next legitimate step is a new-number design with a durable worker and atomic
settlement/custody recovery—not another repository rewrite and not
retrospective promotion of Evaluations 04, 05, or 07.

Plan 10's provider-free Luna Slice A then closed the model/action-shape side of
that restart risk without making a provider call. AE3 now has one exact
structured Luna profile and a strict six-action envelope that enters the
existing semantic action parser and production loop. Its preflight stopped at
a different custody boundary: the shared Codex CLI adapter exposes completed
MCP calls, but not intrinsic command, file-change, or web/search events through
its public result. That means “no intrinsic tool executed” is currently
unknowable to AE3. Treat this as a shared-client observability dependency, not
as permission to reintroduce MCP, scrape provider output privately, dispatch a
canary, or begin recovery machinery against an unverifiable call record.
Evaluation 07's verifier now resolves changed production files to the immutable
input copies already retained in its evidence bundle, so later AE3 development
does not require rewriting the frozen hashes or mutating the terminal evidence.

**Update 2026-10-05.** The paragraph above records the 2026-08 position. The
rest of Plan 10 resolved it: the separately authorized Luna canary passed and
the recoverable worker with atomic per-attempt custody was accepted (ISSUE-001
in `ISSUES.md` is resolved). Plans 19-23 then delivered the local workbench,
and the current comparison attempt is Plan 24's outside-scored trading-vs-solo
experiment; see [the roadmap](MVP_ROADMAP.md) for its state. The five-point bar
above still governs any decision to declare AE3 the successor.

If AE3 produces that evidence while retaining the essential contract/resource
semantics needed for subsequent experiments, decide explicitly whether to mark
AE2 superseded or keep it as a separately active reference runtime. Until then,
the correct disposition is two active lines with different jobs—not another
rewrite.

## Detailed Evidence Map

- Structural rebuild decision (retired, pinned): [REWRITE_SCOPE.md][rewrite-scope]
- Removal order and rationale (retired, pinned): [REMOVAL_SEQUENCE.md][removal-sequence]
- Duplicated AE2 boundaries (retired, pinned): [REMOVAL_03_BOUNDARY_MERGE.md][removal-03]
- Implemented AE3 scope: [IMPLEMENTATION_BASELINE.md](IMPLEMENTATION_BASELINE.md)
- Historical AE3 experiments and caveats (retired, pinned): [CHATGPT_FULL_CONTEXT.md][full-context]
- Inconclusive prescription-ablation result and evidence: [Evaluation 04](evaluations/04_prescription_ablation.md)
- One-shot provider/tool qualification and classifier failure: [Evaluation 05](evaluations/05_provider_tool_qualification.md)
- Terminal paired behavioral attempt and interruption evidence: [Evaluation 07](evaluations/07_behavioral_comparison.md)
- Luna provider-free route inventory and named shared-client blocker: [Plan 10 Slice A evidence](evaluations/evidence/plan10_luna_recovery_gate/README.md)
- AE2 behavioral observations: [`SIMULATION_LEARNINGS.md` at the reviewed commit](https://github.com/BrianMills2718/agent_ecology2/blob/33bbb6de0142435412c02316bd5a43f5733954d8/docs/SIMULATION_LEARNINGS.md)
- AE2 V1 gate: [`V1_ACCEPTANCE.md` at the reviewed commit](https://github.com/BrianMills2718/agent_ecology2/blob/33bbb6de0142435412c02316bd5a43f5733954d8/docs/V1_ACCEPTANCE.md)
- AE1 mechanism code: [`agent_ecology` at the reviewed commit](https://github.com/BrianMills2718/agent_ecology/tree/720920732373292d1353be9a1f8066016b6f5aa8)
- Retired removal records 01-06: recover any of them with
  `git show 28574ed:docs/REMOVAL_0N_<name>.md` (for example
  [Removal 04, dashboard sprawl][removal-04]).

[rewrite-scope]: https://github.com/BrianMills2718/agent_ecology3/blob/28574ed2a65870e8657c5c16e16b7fdd872cc71e/docs/REWRITE_SCOPE.md
[removal-sequence]: https://github.com/BrianMills2718/agent_ecology3/blob/28574ed2a65870e8657c5c16e16b7fdd872cc71e/docs/REMOVAL_SEQUENCE.md
[removal-03]: https://github.com/BrianMills2718/agent_ecology3/blob/28574ed2a65870e8657c5c16e16b7fdd872cc71e/docs/REMOVAL_03_BOUNDARY_MERGE.md
[removal-04]: https://github.com/BrianMills2718/agent_ecology3/blob/28574ed2a65870e8657c5c16e16b7fdd872cc71e/docs/REMOVAL_04_DASHBOARD_SPRAWL.md
[full-context]: https://github.com/BrianMills2718/agent_ecology3/blob/28574ed2a65870e8657c5c16e16b7fdd872cc71e/docs/CHATGPT_FULL_CONTEXT.md
