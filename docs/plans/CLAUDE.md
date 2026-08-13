# Implementation Plans

Track all implementation work here.

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
| 12 | [Luna behavioral feasibility probe](12_luna_behavioral_feasibility.md) | High | 🚧 32-call execution authorized; preflight | Replicated Luna cognition comparison |

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
