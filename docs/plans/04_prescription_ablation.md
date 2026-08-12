# Plan #4: Prescriptive Cognition Ablation

**Status:** In Progress
**Type:** implementation
**Priority:** High
**Blocked By:** None
**Blocks:** Any claim that AE3's observed coordination does not depend on assigned roles or scripted objective cycles

---

## Gap

**Current:** AE3 attributes actions to LLM, fallback, recovery, or forced-explore
origins, but its bootstrap strategy, memory, prompt, output normalizer, and
fallback path actively prescribe specialization, production, pricing, trade,
reuse, and minting. Existing historical readouts therefore cannot distinguish
agent-selected economic behavior from behavior elicited by that cognition
package.

**Target:** Add a backward-compatible `prescribed|minimal` cognition switch,
retain trace links from decisions to full `llm_client` call records, expose an
LLM-originated downstream-value metric, and execute the frozen exploratory
evaluation in `docs/evaluations/04_prescription_ablation.md`.

**Why:** The next useful evidence is not another activity count. It is a
matched comparison that can falsify the claim that paid reuse survives removal
of AE3's strongest behavioral prescriptions.

---

## References Reviewed

- `src/agent_ecology3/world/world.py:30-70,310-645,802-1575,1837-2092` - assigned roles, objective-cycle memory, loop prompt, fallback policy, and LLM syscall boundary.
- `src/agent_ecology3/world/action_executor.py:42-90,451-523` - mutually exclusive decision-origin attribution and loop decision logging.
- `src/agent_ecology3/analysis/emergence_report.py:144-535` - artifact creation-origin and paid downstream-use accounting.
- `src/agent_ecology3/analysis/scarcity_matrix.py:21-749` - matched seeds, call-normalized runs, LLM validity checks, and experiment records.
- `config/prompts/loop_prompt_variant.txt` - recommended but explicitly prescriptive prompt condition.
- `README.md` - historical prescribed-condition results and current recommended profile.
- `docs/LINEAGE_AND_RESTARTS.md` - documented AE2/AE3 restart lessons and the warning against mistaking prompted activity for emergence.
- `CLAUDE.md` and `docs/plans/CLAUDE.md` - repository workflow and plan requirements.

---

## Files Affected

- `src/agent_ecology3/config.py` (modify)
- `src/agent_ecology3/world/world.py` (modify)
- `src/agent_ecology3/world/action_executor.py` (modify)
- `src/agent_ecology3/analysis/emergence_report.py` (modify)
- `src/agent_ecology3/analysis/scarcity_matrix.py` (modify)
- `config/config.yaml` (modify)
- `config/config.tight_scarcity.yaml` (modify)
- `config/config.prescription_ablation.yaml` (create)
- `config/prompts/loop_prompt_minimal.txt` (create)
- `tests/test_config_and_actions.py` (modify)
- `tests/test_runtime_smoke.py` (modify)
- `tests/test_emergence_report.py` (modify)
- `tests/test_scarcity_matrix.py` (modify)
- `README.md` (modify)
- `docs/evaluations/04_prescription_ablation.md` (create, then append results)
- `docs/evaluations/evidence/04_prescription_ablation/` (generated evidence bundle)
- `docs/plans/CLAUDE.md` (modify)

---

## Plan

### Steps

1. Freeze the claim, controls, thresholds, exclusions, call budget, spend budget, and artifact contract before any model call.
2. Add the cognition-mode and provider-budget configuration without changing the default prescribed behavior.
3. Make minimal mode omit assigned roles, objective sequencing, pricing instructions, and choreography-producing fallbacks while retaining the legal action schema, state, feedback, and safety gate.
4. Link each `loop_decision` to its persisted `llm_client` trace and expose downstream paid value whose producing action was `llm_valid`.
5. Add focused tests, then run the prescribed, minimal, and LLM-off conditions exactly as preregistered.
6. Preserve summaries, run IDs, hashes, trace receipts, and an interpretation that is bounded by the frozen non-claims.

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_runtime_smoke.py` | `test_minimal_cognition_omits_prescribed_roles_and_objectives` | Minimal mode removes role/cycle prescriptions from cognition artifacts and generated loop code. |
| `tests/test_runtime_smoke.py` | `test_syscall_logs_and_returns_trace_id_and_budget_controls` | AE3 retains the exact trace link and forwards bounded-call controls. |
| `tests/test_emergence_report.py` | existing metrics test extension | LLM-originated downstream paid value is exposed as a scalar metric. |
| `tests/test_scarcity_matrix.py` | config/CLI extension | Matrices record and override cognition mode. |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| Focused tests above | Cheapest invalidation of the changed public behavior. |
| `pytest -q` | Regression check at integration boundary. |
| `git diff --check` | Reject malformed documentation/code whitespace. |

---

## Acceptance Criteria

- [ ] The default mode reproduces the existing prescribed cognition artifacts and prompt behavior.
- [ ] Minimal mode contains no assigned role, specialization, mandatory discover/read/produce/trade/mint sequence, or automatic price nudge.
- [ ] Minimal invalid-output fallback cannot manufacture cross-agent reads, production, transfers, or mint submissions.
- [ ] Every successful or failed LLM syscall event exposes the deterministic `llm_client` trace ID; loop decisions retain it.
- [ ] The report exposes paid downstream value attributed specifically to an LLM-valid artifact-creation action.
- [ ] All frozen controls and stop rules are evaluated before interpreting the treatment.
- [ ] Raw events, summaries, run IDs, code revision, prompt/config hashes, and trace receipts are preserved.
- [ ] Results are explicitly exploratory and do not change AE2/AE3 lifecycle authority.

---

## Notes

This is a package ablation, not a claim that `minimal` is instruction-free. The
kernel must still communicate the legal action schema and reject invalid
actions. The experiment does not isolate which removed prescription matters;
that requires later component ablations if this probe is informative.
