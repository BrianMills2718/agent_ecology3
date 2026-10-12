---
schema_version: "1.0"
artifact_type: design_plan
id: odd-trace-rule-ids
plan_id: odd-trace-rule-ids
status: proposed
planning_path: requested
method_conformance_receipt: docs/plans/odd-trace-rule-ids.receipt.json
trace_review_criteria:
  - criterion_id: outcome
    expected_outcome: pass
goal:
  outcome: "docs/model/ODD.md names every rule id declared in docs/model/trace.yaml, each beside a passage that states the same behaviour as the trace statement, so the durable-docs check reports zero PROSE-* findings for agent_ecology3"
  canonical_example: "ODD.md section 6.1 now ends its refusal bullet with (RULE-TURN-ACTION-LIMIT), matching trace.yaml rule RULE-TURN-ACTION-LIMIT (at most actions_per_turn, default 4, refused with turn_action_limit)."
  forbidden_substitutes: "claiming success from a check's last line or exit status alone; a change outside the listed files; a commit without the saved check output"
  boundaries: "only these files: docs/model/ODD.md; no irreversible action and no spend; Brian's request as quoted is the scope"
  done_when: "(1) durable_docs_check.py --repo . asserts each trace rule id appears on the prose page: 10 PROSE-RULE-MISSING before, findings=0 required after. (2) Statement conformance: for each of the 10 ids, grep -n -B3 -A1 <id> docs/model/ODD.md is printed beside that id's trace.yaml statement and read side by side; every passage must state the same condition, outcome and code location as the trace (same default, same refusal code, same file:line), with no added behaviour; the 3 passages newly written from the trace (checker failure, strict config, read-only review) are copied from the trace statement wording. (3) make check (pytest + mypy) is run on the committed change with output saved to the session scratchpad log; read its full output: the pytest summary counts (passed/failed/errored/skipped) and mypy result must equal main's run on 35daa11, since a doc-only edit must not change them. The check's full output on the parent commit and on the change commit is committed as docs/plans/odd-trace-rule-ids.check.txt, and the commit is tagged [Goal odd-trace-rule-ids] with an Asked: line quoting the request. python3 \"$SESSION_PLUGIN_ROOT/scripts/durable_docs_check.py\" --repo . --plan docs/plans/odd-trace-rule-ids.md --range 35daa11dd58fe45a937301507b9b3a57931543b9..HEAD exits 0 and its output is in the same file."
  do_not_gate_on: "Brian's review of the plan page; work outside the listed files"
---

# Name every trace rule id on the ODD model page

## When a run fails or surprises us

This procedure is separate from the anticipated failure named in the disproof
under Success and disproof: it applies to any run that fails or surprises us.
Preserve the failed check and its execution trace id. Before selecting a fix,
read the complete inputs, prompts, tool arguments/results, intermediate stages
and final output, including the full check command/output and the changed files.
Cite the observed divergence and classify evidence absent, returned but unused
or contradicted, invalid expectation, or unresolved. An unresolved diagnosis
cannot authorize a causal repair; it permits only further investigation. Bind the targeted repair to a new
traced verification run; retain the failed original. Review every failing or
surprising item and a sample of passes. A complete review is distinct from a
passing run. Criterion `outcome` covers the entire requested success check.

## Actor and result

**Actor:** Brian, who asked for this change.

**Request (verbatim):** Brian 2026-10-12 "i approve" (approving four fixes; the second: make the check compare each model prose page against its trace, ID parity)

**Desired result:** docs/model/ODD.md names every rule id declared in docs/model/trace.yaml, each beside a passage that states the same behaviour as the trace statement, so the durable-docs check reports zero PROSE-* findings for agent_ecology3.

**Stable example:** ODD.md section 6.1 now ends its refusal bullet with (RULE-TURN-ACTION-LIMIT), matching trace.yaml rule RULE-TURN-ACTION-LIMIT (at most actions_per_turn, default 4, refused with turn_action_limit).

## Authority and non-goals

**Authority:** Brian asked for this change in his own repository; one agent makes it.

**Non-goals:** nothing outside the files listed under Vertical and reset. No irreversible action and no spend.

## Requirements

| Id | Requirement | Source | Check | Status |
| --- | --- | --- | --- | --- |
| R1 | docs/model/ODD.md names every rule id declared in docs/model/trace.yaml, each beside a passage that states the same behaviour as the trace statement, so the durable-docs check reports zero PROSE-* findings for agent_ecology3. | asked: Brian 2026-10-12 "i approve" (approving four fixes; the second: make the check compare each model prose page against its trace, ID parity) | the success check under Success and disproof, its output saved as `docs/plans/odd-trace-rule-ids.check.txt` | planned, not yet run |

Requirements the change's own claims imply: none beyond R1; the change presents nothing as following a standard, schema or contract.

## Durable documents

This repository declares durable documents (`durable_documents` in `.agentic/repo.yaml`); its declared roles are `goal`, `requirements`, `system_model`, `decisions`, `plans`. Each role named below is one of them (checked by quick-adopt).

Durable documents: system_model#RULE-TURN-ACTION-LIMIT, system_model#RULE-READ-PRICE-PAID, system_model#RULE-TRADING-OFF-CLOSES-CROSS-TRADE, system_model#RULE-FIRST-PASS-PAID, system_model#RULE-ROYALTY-REQUIRES-CALL, system_model#RULE-CHECKER-FAILURE-STOPS, system_model#RULE-PILOT-PAYS-ONLY-SUPPORTED, system_model#RULE-CONFIG-STRICT, system_model#RULE-MODEL-MATCHES-EVENTS, system_model#RULE-REVIEW-READ-ONLY

At completion, `python3 "$SESSION_PLUGIN_ROOT/scripts/durable_docs_check.py" --repo . --plan docs/plans/odd-trace-rule-ids.md --range 35daa11dd58fe45a937301507b9b3a57931543b9..HEAD` must exit 0; its full output is appended to `docs/plans/odd-trace-rule-ids.check.txt` (the durable-documents check, Plan #61; `durable_docs_check.py` ships in the Company Planning plugin).

## Success and disproof

**Success evidence:** (1) durable_docs_check.py --repo . asserts each trace rule id appears on the prose page: 10 PROSE-RULE-MISSING before, findings=0 required after. (2) Statement conformance: for each of the 10 ids, grep -n -B3 -A1 <id> docs/model/ODD.md is printed beside that id's trace.yaml statement and read side by side; every passage must state the same condition, outcome and code location as the trace (same default, same refusal code, same file:line), with no added behaviour; the 3 passages newly written from the trace (checker failure, strict config, read-only review) are copied from the trace statement wording. (3) make check (pytest + mypy) is run on the committed change with output saved to the session scratchpad log; read its full output: the pytest summary counts (passed/failed/errored/skipped) and mypy result must equal main's run on 35daa11, since a doc-only edit must not change them.

**Trace review:** two runs of the success check above are judged from their full output: one on the parent commit before the change (the disproof run: it must show the defect or the check failing, which proves the check can fail) and one on the commit that makes the change (the success run); no model, agent or LLM pipeline runs under this plan. Where the trace lives: the check's complete output, with the exact command and its exit status, is saved as `docs/plans/odd-trace-rule-ids.check.txt` and committed with the change. What must be seen in it beyond the final result: the command ran against the files listed under Vertical and reset at that commit, each check or test it reports appears by name with its result and none is skipped, and the exit status matches; for each model element listed under System model, the output shows what that line says. Both runs are saved in that one file, each headed by its commit: the disproof condition is judged from both (it holds if the success run still shows the defect, or if the before run already passes, meaning the check cannot detect it), and success from the success run.

**Disproof:** Any PROSE-RULE-MISSING finding remaining; an id on ODD.md that trace.yaml does not declare; a passage beside an id whose condition, default, refusal code or file:line differs from its trace statement; or make check counts differing from main's.

## System model

**System model:** `docs/model/ODD.md`, a file in this repository describing this repository only (not a shared model). Reachable from the documentation entry point `wiki/index.md`, which links `docs/model/ODD.md`.

**Model elements this change adds, changes or relies on, and what the saved check output must show of each:**

- none -- documentation-only: names existing trace rule ids on the prose page; no entity, process, record or view changes

**Views, freshness and reconciliation:** the applicable view is the requirement-to-verification link in the Requirements table (each requirement and the check that shows it, the check being source-linked by its command); no other view applies because the change adds, changes or relies on no entity, process, record, event or view beyond the elements listed above. Freshness: the model's drift test (`tests/test_model_declaration.py`) runs inside the success check and its output is in the saved check file. If an element above is added, removed or renamed, the model, its view coverage and the saved check output are reconciled in the same commit, and otherwise the model needs no update because the elements keep their meaning.

## Capability reuse

Checked against the capability catalogue in agentic-capability-architecture-canonical (`reuse_candidates.yml` and `capability_registry.yml`):

- No catalogue entry fits, because this is a one-page documentation edit to an existing model page
- What the work needs that no entry provides: edits to this repository's own files (`docs/model/ODD.md`); catalogue entries are cross-project capabilities, and none edits a repository's own source.

## Uncertainties

Material uncertainties. This one is the complete set; it is material because a file outside the list would
make the change exceed this plan's scope.

| Material uncertainty | Owner or resolving evidence |
| --- | --- |
| Whether the change needs files beyond the list below; if so it is out of scope for this plan | Resolved before editing: git diff --stat: 1 file changed (docs/model/ODD.md), 25 insertions, 7 deletions |

## Vertical and reset

One vertical over these files (and the saved check output, `docs/plans/odd-trace-rule-ids.check.txt`):

- `docs/model/ODD.md`

The vertical delivers: docs/model/ODD.md names every rule id declared in docs/model/trace.yaml, each beside a passage that states the same behaviour as the trace statement, so the durable-docs check reports zero PROSE-* findings for agent_ecology3. It is done when this holds: (1) durable_docs_check.py --repo . asserts each trace rule id appears on the prose page: 10 PROSE-RULE-MISSING before, findings=0 required after. (2) Statement conformance: for each of the 10 ids, grep -n -B3 -A1 <id> docs/model/ODD.md is printed beside that id's trace.yaml statement and read side by side; every passage must state the same condition, outcome and code location as the trace (same default, same refusal code, same file:line), with no added behaviour; the 3 passages newly written from the trace (checker failure, strict config, read-only review) are copied from the trace statement wording. (3) make check (pytest + mypy) is run on the committed change with output saved to the session scratchpad log; read its full output: the pytest summary counts (passed/failed/errored/skipped) and mypy result must equal main's run on 35daa11, since a doc-only edit must not change them.

Make the change, run the success check before and after it, commit. Reset: `git revert` of the commit. Not pursued: anything outside these files. This plan adds no coordinated-work ceremony: no work-unit graph, no review or release contract, no claim beyond the repository's own rules.

## Activation facts

Each fact, with its value and why:

- `shared_mechanism`: false -- the change edits only the listed files and adds no contract, algorithm or mechanism other code uses.
- `empirical_comparison_proposed`: false -- no alternatives are compared; the success check verifies the one change.
- `llm_central`: false -- the change makes no model call.
- `irreversible_or_spend_action`: false -- the change is reverted by `git revert` and spends nothing.
- `claims_external_standard`: false -- the work claims no external standard, schema or contract.
- `aes_governed_target`: false -- this repository has no `.aes/target.yaml` (checked by quick-adopt).
- `durable_documents_declared`: true -- derived, `.agentic/repo.yaml` has `durable_documents`; see Durable documents.

