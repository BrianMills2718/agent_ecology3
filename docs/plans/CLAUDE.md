# Implementation Plans

Track all implementation work here.

**Current direction:** [Agent Ecology 3 Product Roadmap](../MVP_ROADMAP.md) is
the canonical outcome and priority authority. Completed plans below are
supporting history. Plans 19–21 completed the local MVP, durable reopen, and
paused dashboard-launch boundaries. The resumed Plan 21 run was invalidated by
a deleted-worker-cwd failure concealed by substitute actions. Plan 22 is the
active repair frontier.

## Gap Summary

| # | Name | Priority | Status | Blocks |
|---|------|----------|--------|--------|
| 1 | [Example Plan](01_example.md) | Medium | Planned | - |
| 2 | [Mint scorer llm_client migration](02_mint_scorer_llm_client.md) | High | ✅ Complete | - |
| 3 | [Repository lineage and restart lessons](03_lineage_and_restart_lessons.md) | High | ✅ Complete | AE2/AE3 lifecycle decision |
| 4 | [Prescriptive cognition ablation](04_prescription_ablation.md) | High | ✅ Complete | Evidence independent of assigned roles/objective cycles |
| 5 | [Experiment instrument repair and provider qualification](05_experiment_instrument_repair.md) | High | ✅ Complete | Fresh provider qualification with public-readback control |
| 6 | [Public-readback provider qualification](06_public_readback_qualification.md) | High | ✅ Complete | Fresh prescribed-versus-minimal behavioral evaluation design/preregistration |
| 7 | [Behavioral comparison preregistration](07_behavioral_comparison_preregistration.md) | High | ✅ Complete | Evaluation 07 implementation and separately authorized execution |
| 8 | [Behavioral comparison runner](08_behavioral_comparison_runner.md) | High | ✅ Complete | Separately authorized Evaluation 07 execution |
| 9 | [Behavioral comparison execution](09_behavioral_comparison_execution.md) | High | ✅ Complete (invalid) | New-number evaluation only |
| 10 | [Luna Medium compatibility and recovery gate](10_luna_medium_recovery_gate.md) | High | ✅ Complete | Luna-specific qualification and scarcity calibration |
| 11 | [Luna scarcity calibration](11_luna_scarcity_calibration.md) | High | ✅ Calibration complete | New-number Luna behavioral comparison |
| 12 | [Luna behavioral feasibility probe](12_luna_behavioral_feasibility.md) | High | ✅ Complete (invalid at prescribed 14/16) | New-number design only |
| 13 | [Receipt and fallback contract repair](13_receipt_and_fallback_contract.md) | High | ✅ Complete | New behavioral evaluation |
| 14 | [Luna behavioral feasibility repair](14_luna_behavioral_feasibility_repair.md) | High | ✅ Complete (invalid pair) | New-number design only |
| 15 | [Hard call cap](15_hard_call_cap.md) | High | ✅ Complete | Dashboard-visible matched pair |
| 16 | [Completed run review](16_completed_run_review.md) | High | ✅ Complete | Human MVP review |
| 17 | [Useful completed-run review](17_useful_run_review.md) | High | ✅ Complete | Human review of the Luna Medium PoC |
| 18 | [Ecosystem operator dashboard](18_ecosystem_operator.md) | High | ✅ Complete | Useful human observation of an AE3 run |
| 19 | [Live economic MVP vertical](19_live_economic_mvp.md) | Critical | ✅ Complete — authentic run signed off | Repeatable local workbench |
| 20 | [Single-run archive reopen](20_single_run_archive_reopen.md) | Critical | ✅ Complete | Dashboard launch |
| 21 | [Fixed-profile dashboard launch](21_dashboard_launch.md) | Critical | ✅ Complete | Authorized repeat-run observation |
| 22 | [Fail-loud authentic runs](22_fail_loud_authentic_runs.md) | Critical | Provider-free complete; canary pending | One-call Luna canary authorization |

## Status Key

| Status | Meaning |
|--------|---------|
| Planned | Ready to implement |
| In Progress | Being worked on |
| Blocked | Waiting on dependency |
| Complete | Implemented and verified |

## Creating a New Plan

1. Copy `TEMPLATE.md` to `NN_name.md`
2. Fill in gap, steps, required tests
3. Add to this index
4. Commit with `[Plan #N]` prefix

## Trivial Changes

Not everything needs a plan. Use `[Trivial]` for:
- Less than 20 lines changed
- No changes to `src/` (production code)
- No new files created

```bash
git commit -m "[Trivial] Fix typo in README"
```

## Completing Plans

```bash
python scripts/meta/complete_plan.py --plan N
```

This verifies tests pass and records completion evidence.
