# Resource Accounting: Real vs Pseudo

Date: 2026-02-23

## Question

Should Agent Ecology 3 use real resource accounting, pseudo approximations, or a mix?

## Option A: Real accounting everywhere

Definition:
- Measure actual usage whenever possible (real token usage, real call counts, real execution time, real bytes).

Pros:
1. Better economic realism and incentive integrity.
2. Fewer strategy exploits from predictable approximations.
3. Better auditability for experiments.

Cons:
1. Higher implementation complexity and more integration points.
2. Vendor/API dependency for exact values.
3. More edge cases (missing usage fields, retries, partial failures).

## Option B: Pseudo approximations everywhere

Definition:
- Use deterministic estimates (chars->tokens, fixed call cost, fixed CPU weights, static disk factors).

Pros:
1. Simple and stable implementation.
2. Easy to test and reproduce.
3. Lower integration coupling.

Cons:
1. Lower realism.
2. Easier to game if agents infer cost formula.
3. Potential drift from real-world economics.

## Option C (Recommended): Hybrid measured-first accounting

Definition:
- Use real measurements where they are cheap/reliable.
- Use calibrated approximations where exact accounting is expensive or unavailable.

Recommended split:
1. LLM calls: real call count + real usage/cost when provider returns usage; fallback estimate when absent.
2. LLM tokens: provider-reported tokens when available; fallback `chars/4` estimate.
3. LLM budget: real billed cost when available; in subscription-included mode, settle against configurable estimated units so budget scarcity can still bind.
4. CPU: measured process CPU seconds (already available).
5. Disk: real UTF-8 byte counts (already available).

Why this is best here:
1. Keeps core architecture simple.
2. Preserves realism where it matters most (LLM economics).
3. Avoids over-engineering for weak-signal metrics.

## Effort Comparison (rough)

1. Full-real everywhere: `medium-high`.
2. Full-pseudo everywhere: `low`.
3. Hybrid measured-first: `low-medium`.

Given expected impact, hybrid provides most value per engineering hour.

## Guardrails to keep pseudo realistic

1. Store both `estimated_*` and `actual_*` when available.
2. Track per-run estimation error for calibration.
3. Make fallback formulas explicit and versioned.
4. Never silently mix units; enforce typed metric names.

## Verification Note

Last verified: 2026-08-11

- `world.call_llm_as_syscall` now passes `max_retries=0` explicitly for agent-SDK models.
- This does not change accounting semantics; it only removes repeated retry-disabled warning noise while preserving side-effect-safe no-retry behavior.
- `world.call_llm_as_syscall` and `world.call_llm_as_syscall_async` now share
  `_prepare_llm_syscall`, `_llm_call_kwargs`, `_settle_llm_syscall`, and
  `_fail_llm_syscall`. Both routes reserve the same estimated budget/tokens,
  reconcile the same measured usage/cost, and retain the same trace fields.
- Async cancellation refunds the in-flight reservation and re-raises the
  cancellation; normal runner shutdown drains the call instead of cancelling
  it. Evaluation 05 observed 32 serial calls for USD 0.0359061 without changing
  these accounting rules.
