# Plan #7: Behavioral Comparison Preregistration

**Status:** Complete
**Type:** evaluation design
**Priority:** High
**Blocked By:** None
**Blocks:** Evaluation 07 implementation and any new behavioral provider dispatch

---

## Gap

**Current:** Evaluation 06 qualified the public-readback provider/prompt/tool
instrument for both cognition prompts. Evaluation 04 never reached its minimal
treatment, so AE3 still has no matched evidence separating its prescriptive
cognition package from minimally prescribed behavior.

**Target:** Freeze a new held-out paired comparison whose only behavioral
treatment is `prescribed` versus `minimal`, with fixed attempts, real scarcity,
full trace custody, balanced order, explicit invalid-pair handling, and a
decision rule capable of detecting only a large effect.

**Why:** The remaining uncertainty is empirical. Another architecture rewrite,
provider qualification, or activity-only smoke test cannot answer whether the
prescriptions materially change paid downstream reuse.

---

## References Reviewed

- `docs/evaluations/04_prescription_ablation.md` — inconclusive first assay and
  its event-loop, truncation, and custody failure modes.
- `docs/evaluations/06_public_readback_qualification.md` and signoff — qualified
  MiniMax M3 prompt/tool boundary and narrow decision authorization.
- `src/agent_ecology3/analysis/scarcity_matrix.py` — successful-call stopping,
  run validity, matched-seed metadata, and evidence outputs.
- `src/agent_ecology3/analysis/emergence_report.py` — decision-origin and paid
  downstream-value definitions.
- `src/agent_ecology3/simulation/runner.py` — serial world execution and
  async-safe provider monitoring.
- `src/agent_ecology3/world/world.py` — the exact prescribed/minimal package,
  fallback behavior, public trace IDs, and provider budgets.
- `docs/LINEAGE_AND_RESTARTS.md` — experiment validity and scarcity guardrails.

---

## Files Affected

- `docs/evaluations/07_behavioral_comparison.md` (create)
- `config/config.behavioral_comparison_07.yaml` (create)
- `config/evaluations/07_behavioral_cases.json` (create)
- `docs/plans/07_behavioral_comparison_preregistration.md` (create)
- `docs/plans/CLAUDE.md` (modify)
- `README.md`, `docs/CHATGPT_FULL_CONTEXT.md`, and
  `docs/LINEAGE_AND_RESTARTS.md` (record preregistered/not-run status)

No runtime or analysis implementation and no provider execution belong to this
plan.

---

## Plan

1. State the causal package claim, decision outcomes, non-claims, and target
   population.
2. Freeze a held-out 12-pair schedule plus two ordered reserve pairs, balanced
   condition order, exact attempt/cost ceilings, and no-rerun behavior.
3. Freeze metric definitions, scarcity manipulation check, deterministic and
   runtime controls, trace contract, invalid-run rules, and uncertainty method.
4. Define the future runner/reproducer interface and executable acceptance
   evidence without implementing or dispatching it.
5. Commit and push the preregistration before any Evaluation 07 model call.

---

## Required Checks

| Check | Purpose |
|---|---|
| JSON/YAML parse and config load | Inputs are syntactically and contract valid. |
| Pair-schedule invariant check | 14 unique held-out seeds, balanced order, 12 primary plus two reserve pairs. |
| Hash and leakage check | Frozen prompts/config are exact and seeds do not appear in prior evaluation artifacts. |
| `pytest -q` | Documentation/config addition does not break the current repository. |
| document coupling and `git diff --check` | Repository process gates remain satisfied. |

---

## Acceptance Criteria

- [x] The claim, decision, population, minimum useful effect, and non-claims are
      explicit.
- [x] Conditions differ only in the cognition package and prompt assigned by
      that package.
- [x] The execution schedule, reserves, exact attempts, budget, stopping rule,
      and invalid-pair behavior are frozen.
- [x] Positive, negative, corruption, public-readback, scarcity, leakage, and
      trace controls have deterministic pass/fail behavior.
- [x] Primary and secondary metrics, uncertainty, and all allowed decision
      outcomes are fixed before implementation.
- [x] Future implementation cannot change world, prompt, action-schema, model,
      or threshold surfaces without requiring a new evaluation number.
- [x] Independent `eval-decision-signoff` is required before acting on results.
- [x] No Evaluation 07 provider call is made in this plan.

---

## Failure Handling

This preregistration does not authorize execution. Any material design change
after this commit—including different seeds, prompts, thresholds, model,
attempt count, scarcity endowment, reserve policy, or readout—requires a new
evaluation number. A future implementation may add only the orchestration,
verification, and evidence-export surfaces specified by the preregistration.

---

## Completion Evidence

- The config loads through AE3's typed config contract; JSON/YAML parsing and
  schedule invariants pass.
- Fourteen seeds are unique, balanced 7/7 by first condition, and absent from
  prior tracked evaluation inputs and evidence.
- The 448-attempt and USD 1.68 maxima reproduce from the frozen pair/run caps.
- Exact paired-test boundary cases were enumerated before execution; the large-
  effect rule requires at least six net discordant pairs and `p <= 0.05`.
- Frozen prompt, config, case, Eval06 manifest, and Eval06 signoff hashes are
  recorded in the preregistration.
- The existing repository regression suite passed: 76 tests.
- No runtime code was changed and no provider call was made.
