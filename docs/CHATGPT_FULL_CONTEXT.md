# Agent Ecology 3: Full Context Handoff for ChatGPT

Date: 2026-02-22
Primary repo: `/home/brian/projects/agent_ecology3`
Previous repo: `/home/brian/projects/agent_ecology2`
Historical reference: `/home/brian/projects/archive/agent_ecology`

## 1. What this project is trying to do

Agent Ecology 3 (AE3) is an economy simulation substrate where autonomous agents (principals) should become strategically self-interested and adapt under real scarcity.

The target behavior is emergence, not scripted choreography:
- Specialization should emerge because of incentives and scarcity.
- Trade should emerge because self-sufficiency is expensive.
- Cooperation should be discovered when utility-positive, not hard-coded as "be cooperative".

The core hypothesis:
- If resource scarcity and incentive structure are correct, higher-order behaviors (pricing, exchange, comparative advantage, planning) should emerge without forcing explicit scripts like "always transfer".

## 2. Operator principles and constraints (important)

These are hard constraints from the operator and must be respected in advice:

1. Contracts govern access rights.
- Do not reason from an ownership-centric model.
- In AE2 docs, "owner" is explicitly an informal shortcut, not the core rights model.

2. Scarce resources should be initially allocated, then reallocated by contracts/trade.
- Kernel-level "fairness for fairness" is not a goal.
- Queue fairness or scheduler fairness is not the primary objective.

3. Emergence over prescription.
- Avoid recommendations that hard-code behavior templates and then call that "emergence".
- Instrument and nudge incentives, do not script economic outcomes.

4. Keep architecture simple.
- Avoid overengineering before strong evidence.
- Prefer obvious high-leverage wins and defer elaborate frameworks until core emergence is robust.

5. Real accounting preferred over pseudo when practical.
- If equal effort, prefer real measured accounting.
- If not practical, use realistic approximations that are explicit and calibrated.

## 3. Why AE3 exists (rewrite rationale)

AE3 is a clean rebuild of AE2 due code smell and architecture sprawl. The rewrite scope kept kernel essentials and removed runtime-adjacent complexity.

Approved removals from AE2 applied in AE3:
1. Runtime-adjacent governance/process scaffolding.
2. Legacy compatibility shims and one-off dispatch pathways.
3. Duplicated authority boundaries (merged to canonical paths).
4. Dashboard frontend sprawl.
5. Dormant non-essential boot subsystems in core path.
6. Full backward config compatibility requirement.

Deferred extension (explicitly postponed):
- External capability runtime in core boot path. Keep as optional extension after core AE3 emergence is proven.

## 4. Current AE3 architecture

Core modules:
- `src/agent_ecology3/world/world.py`
- `src/agent_ecology3/world/action_executor.py`
- `src/agent_ecology3/world/actions.py`
- `src/agent_ecology3/world/ledger.py`
- `src/agent_ecology3/world/rates.py`
- `src/agent_ecology3/world/contracts.py`
- `src/agent_ecology3/world/mint.py`
- `src/agent_ecology3/simulation/runner.py`
- `src/agent_ecology3/analysis/emergence_report.py`
- `src/agent_ecology3/analysis/scarcity_matrix.py`

Kernel primitives:
- Principals with scrip and resources.
- Artifacts (typed, executable/non-executable, contract-governed).
- Contract engine for permission checks.
- Mint auction subsystem.
- Autonomous loop artifacts (`has_loop=True`).
- JSONL event log as canonical telemetry.

Action set used by loop policy:
- `write_artifact`
- `read_artifact`
- `transfer`
- `transfer_resource`
- `submit_to_mint`
- `query_kernel`

Loop output is action-gated to the above set. Disallowed LLM actions are rewritten to fallback actions.

## 5. Agent cognition model currently implemented

Each principal is bootstrapped with:
- `*_strategy`
- `*_state`
- `*_notebook`

Role profiles exist (rotated by slot):
- `market_maker`
- `toolsmith`
- `auditor`
- `scout`

State tracks objective cycle:
- `discover -> cross_agent_read -> produce -> trade -> mint`

Loop memory tracks:
- recent actions, action counts, stagnation count
- last result success/error
- objective completion state
- notebook key facts and journal

Current loop policy includes:
- LLM decision path (tool-call preferred)
- normalization of malformed LLM payloads
- fallback action path
- forced-explore safety nudges
- in-memory recent-feedback summary (no hot-path event-log scans)
- optional cooldown (currently default `0.0`)

## 6. Scarcity and accounting model

### 6.1 Resources in play

- Stock resource: `llm_budget` (transferable via `transfer_resource`)
- Rate-limited resources: `llm_calls`, `llm_tokens`, `cpu_seconds`
- Scrip balances (transferable)
- Disk quota

### 6.2 LLM syscall accounting path

LLM path in `World.call_llm_as_syscall`:
1. Estimate tokens/cost for preflight reservation.
2. Reserve `llm_budget` and consume rate units (`llm_calls`, `llm_tokens`).
3. Call `llm_client.call_llm`.
4. Reconcile reserved units against measured usage/cost.
5. Log `llm_syscall` event with accounting fields.

### 6.3 Real vs pseudo decision

Adopted model is hybrid measured-first:
- Real provider usage/cost when available.
- Explicit fallback estimates when unavailable.
- Internal accounting constants tracked in `docs/ACCOUNTING_CONSTANTS.md` with update triggers.

### 6.4 Subscription-mode fix (important recent change)

Problem observed:
- In `subscription_included` billing mode (Claude Code / Codex OAuth), provider-reported marginal USD often `0`, which made `llm_budget` non-binding after refund reconciliation.

Fix implemented:
- Added `llm.subscription_budget_charge_mode` with modes:
  - `actual`
  - `estimated` (default)
  - `none`
- Added `llm.subscription_estimated_cost_multiplier` (default `1.0`).
- New syscall fields logged:
  - `budget_charge_basis`
  - `budget_settle_cost`

Current default behavior:
- For subscription-included calls, `llm_budget` depletes by estimated internal units (not provider USD), preserving scarcity pressure.

This addresses the operator requirement: subscription agents must still face budget depletion and freezing behavior like others.

## 7. Experiment process and metrics

### 7.1 Tooling

- `scarcity_matrix`: repeated runs + aggregate + KPI lock.
- `emergence_report`: per-run metrics and experiment logging.
- Integration with `llm_client` experiments (`start_run`, `log_item`, `finish_run`, compare/list/detail).

### 7.2 Entropy metric definition

`loop_action_entropy_bits` is Shannon entropy over `loop_decision` action distribution, not low-level action spam.

This was intentionally changed to avoid misleading entropy from instrumentation noise.

### 7.3 KPI lock (current thresholds)

From `scarcity_matrix.evaluate_kpi_lock`:
- `loop_action_entropy_bits_mean >= 2.1`
- `mint_submissions_mean >= 3.0`
- `decision_success_rate_min >= 0.98`
- `repeat_error_rate_max <= 0.0`
- Exchange pressure passes if any:
  - `cross_transfer_amount_mean >= 3.0` (scrip)
  - `cross_llm_budget_transfer_amount_mean >= 0.5`
  - `resource_transfers_total_mean >= 2.0`

### 7.4 Important caveat

KPI lock is a guardrail, not proof of true economic emergence.
- High entropy can come from exploration noise.
- Transfers can be low-information pulses.
- Need qualitative behavior inspection and longer-horizon dynamics.

## 8. Key empirical results so far

### 8.1 DeepSeek confidence baseline (5 runs, 900s, target 80 LLM calls)

Summary file:
- `logs/confidence_baseline_deepseek_80calls_runs5_1771776729_summary.json`

Aggregate highlights:
- `loop_action_entropy_bits mean: 2.476`
- `cross_transfer_amount mean: 17.2`
- `cross_llm_budget_transfer_amount mean: 3.3`
- `resource_transfers_total mean: 10.6`
- `mint_submissions mean: 15.0`
- `decision_success_rate min: 1.0`
- `repeat_error_rate max: 0.0`
- KPI lock: pass

### 8.2 Tight scarcity profile (3 runs, 900s, target 80 calls)

Profile:
- `config/config.tight_scarcity.yaml`

Summary file:
- `logs/confidence_tight_scarcity_deepseek_80calls_runs3_1771779132_summary.json`

Aggregate highlights:
- `loop_action_entropy_bits mean: 2.496`
- `cross_transfer_amount mean: 17.666667`
- `cross_llm_budget_transfer_amount mean: 0.966667`
- `resource_transfers_total mean: 9.666667`
- `mint_submissions mean: 15.333333`
- KPI lock: pass

### 8.3 Subscription accounting validation (Opus, 1 run, target 20 calls)

Summary file:
- `logs/validation_subscription_budget_opus_20calls_1771781521_summary.json`

Observed:
- `billing_mode: subscription_included` on llm syscalls
- `actual_cost_sum: 0.0`
- `charged_cost_sum: 0.100374` (internal budget depletion)
- `budget_charge_basis: subscription_estimated` across calls
- KPI lock: pass

This confirms subscription-mode scarcity is now binding.

### 8.4 Post-prompt adjustment quick validations

DeepSeek (20-call target):
- `logs/validation_post_prompt_deepseek_20calls_1771781920_summary.json`
- KPI lock pass

Opus (20-call target):
- `logs/validation_post_prompt_opus_20calls_1771782046_summary.json`
- KPI lock pass
- `charged_cost_sum: 0.107196` in subscription mode

## 9. What is still weak / unresolved

1. Market quality versus quantity.
- Transfers and minting happen, but not all exchanges are clearly high-value specialization-driven trades.

2. Price-setting behavior is inconsistent.
- DeepSeek tends to set `read_price` more often in write decisions than recent Opus runs.
- Opus can still trade and mint without consistently monetizing artifact outputs.

3. Role differentiation is present but still lightweight.
- Better than identical prompts, but likely not enough to force strong comparative advantage.

4. Horizon sensitivity.
- Some emergent behavior likely needs longer runs and stronger cumulative memory effects.

5. KPI validity limitations.
- Current KPI lock is useful for regression detection but insufficient as sole emergence proof.

6. Potential model hobbles still under scrutiny.
- Action gating / explore nudges may occasionally suppress richer model initiative.
- Need careful tuning to avoid over-constraining powerful agent SDK models.

## 9A. Advisory resolution from external critique (implemented now)

The latest external critique was accepted in-part and converted into Phase 1 instrumentation.

Accepted and implemented:
- Measure policy injection directly rather than inferring from entropy alone.
- Add MECE loop-decision origin labels:
  - `llm_valid`
  - `llm_invalid_fallback`
  - `forced_explore`
  - `recovery`
  - `fallback_without_llm`
- Log forced-explore reason codes per decision.
- Add value-weighted exchange metrics (paid read/invoke scrip flow on cross-principal edges).
- Add reuse-weighted artifact value and specialization HHI over revenue-by-artifact-type.
- Add mint downstream value proxy (minted artifacts that later earn paid cross-principal consumption).
- Add attribution of value by decision origin and `forced_explore_value_share`.
- Add forced-explore mode knob for falsification:
  - `llm.loop_forced_explore_mode: baseline | reduced | off`

Accepted with scope limits:
- Keep this phase as instrumentation and reporting first; no escrow primitive, no mint mechanism rewrite, no quota-voucher market rewrite in this phase.
- Keep existing second-price + redistribution mint behavior unchanged until metrics show a specific bottleneck.
- Keep cost accounting tied to measured external scarcity signals (tokens/calls/cpu/budget policy), not synthetic per-role discounts.

Rejected/deferred in this phase:
- Immediate mechanism redesign (escrow swaps, tradable rolling-window quotas) before confound isolation.
- KPI-lock redesign before collecting value-weighted baselines.

## 9B. Phase 1 completion hardening (implemented now)

Additional instrumentation hardening now implemented:
- `scarcity_matrix` supports matched-condition deterministic policy seeds:
  - `--seed-base`
  - `--seed-step`
  - wired to `llm.loop_policy_seed` per run
- Added optional LLM path preflight:
  - `--llm-preflight auto|on|off`
  - auto activates when loop LLM is on and LLM-engagement validity thresholds are active
  - fails fast on broken model path/auth before long matrix jobs
- Added run-level LLM-engagement validity gating:
  - `--min-llm-calls`
  - `--min-llm-valid-decisions`
  - `--min-llm-attempt-rate`
  - `--min-llm-valid-decision-rate`
  - `--invalid-run-policy warn|drop|fail`
- Matrix summaries now expose:
  - `runs_included_in_aggregate`
  - `runs_excluded_from_aggregate`
  - per-run `llm_validity` checks and `included_in_aggregate` flags
- Auto-threshold safety:
  - if `--target-llm-calls > 0` and no explicit `--min-llm-calls` is set, matrix applies `min_llm_calls=1` to prevent invalid emergence inference from zero-call runs.

## 10. Major design debates currently active

### 10.1 Bidding versus allocation-first resource philosophy

Tension:
- Principle: all scarce resources allocated then contracted.
- Alternative: kernel-level bid-based admission for some pathways.

Current stance:
- Be cautious with kernel-level admission bidding as default.
- Mint bidding can still be valid if mechanism goals are explicit.

Key tradeoff:
- If bids are burned, mechanism is deflationary.
- If bids are redistributed (for example as UBI or rebates), pressure profile differs.

Need advice on mechanism design consistent with stated philosophy.

### 10.2 Fairness/cooldown controls

- Operator priority is evolutionary optimization under scarcity, not fairness.
- Cooldown exists as optional tuning knob; default is `0.0`.
- Avoid fairness-heavy scheduler complexity unless it directly supports the scarcity objective.

### 10.3 Real accounting boundaries

Not fully solvable at call time:
- Invoice-level truth (credits, discounts, regional adjustments) is not always available in real time.

Current practical compromise:
- Real where available.
- Explicit fallback estimates.
- Subscription mode with explicit internal budget policy.

## 11. Historical lessons carried forward from AE2/legacy

From AE2 simulation learnings:
- Cognitively identical agents + self-contained goals + non-binding scarcity suppress cooperation.
- Prescriptive rule-set prompts can create deadlocks/crawling.
- Goal+context and memory scaffolding are more promising than rigid scripts.
- Lever for emergence is agent cognitive architecture under real scarcity, not brute forcing physics alone.

From original archive (`archive/agent_ecology`):
- Useful for policy/observation ideas, but architecture is substantially different and should not be reintroduced wholesale.

## 12. Practical commands for reproduction

### 12.1 Run simulation

```bash
cd /home/brian/projects/agent_ecology3
python run.py --duration 120 --agents 4 --llm-loop on
```

### 12.2 Run scarcity matrix

```bash
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix \
  --config config/config.yaml \
  --runs 5 \
  --duration 900 \
  --agents 4 \
  --model openrouter/deepseek/deepseek-chat \
  --target-llm-calls 80 \
  --llm-loop on \
  --loop-llm-cooldown 0 \
  --seed-base 100 \
  --seed-step 1 \
  --llm-preflight auto \
  --min-llm-calls 1 \
  --min-llm-valid-decisions 5 \
  --invalid-run-policy drop \
  --prefix confidence_baseline_deepseek_80calls_runs5 \
  --pretty
```

### 12.2A Falsification matrix starter (Phase 1)

Baseline (current guardrails):
```bash
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix \
  --config config/config.yaml \
  --runs 5 \
  --duration 900 \
  --agents 4 \
  --model openrouter/deepseek/deepseek-chat \
  --target-llm-calls 80 \
  --llm-loop on \
  --loop-forced-explore baseline \
  --seed-base 100 \
  --seed-step 1 \
  --llm-preflight auto \
  --min-llm-calls 1 \
  --min-llm-valid-decisions 5 \
  --invalid-run-policy drop \
  --pretty
```

Reduced forced-explore:
```bash
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix \
  --config config/config.yaml \
  --runs 5 \
  --duration 900 \
  --agents 4 \
  --model openrouter/deepseek/deepseek-chat \
  --target-llm-calls 80 \
  --llm-loop on \
  --loop-forced-explore reduced \
  --seed-base 100 \
  --seed-step 1 \
  --llm-preflight auto \
  --min-llm-calls 1 \
  --min-llm-valid-decisions 5 \
  --invalid-run-policy drop \
  --pretty
```

Forced-explore off:
```bash
PYTHONPATH=src python -m agent_ecology3.analysis.scarcity_matrix \
  --config config/config.yaml \
  --runs 5 \
  --duration 900 \
  --agents 4 \
  --model openrouter/deepseek/deepseek-chat \
  --target-llm-calls 80 \
  --llm-loop on \
  --loop-forced-explore off \
  --seed-base 100 \
  --seed-step 1 \
  --llm-preflight auto \
  --min-llm-calls 1 \
  --min-llm-valid-decisions 5 \
  --invalid-run-policy drop \
  --pretty
```

Subscription scarcity sweep:
```bash
# Run the same matrix with llm.subscription_estimated_cost_multiplier in {0.5, 1.0, 2.0, 4.0}.
# Keep seed handling and other params fixed across conditions.
```

### 12.2B Fast diagnostic results (2026-02-22)

Because OpenRouter DeepSeek was rate-limited (`403 key limit exceeded`), the matched-condition diagnostics below were run on `claude-code/opus` with preflight enabled.

Forced-explore falsification (same seed/target for all):
- Baseline:
  - `logs/phase1_diag_baseline_opus_s100_t4_1771792195_summary.json`
  - `forced_explore_rate: 0.25`
  - `llm_valid_decision_rate: 0.75`
- Reduced:
  - `logs/phase1_diag_reduced_opus_s100_t4_1771792256_summary.json`
  - `forced_explore_rate: 0.0`
  - `llm_valid_decision_rate: 1.0`
- Off:
  - `logs/phase1_diag_off_opus_s100_t4_1771792313_summary.json`
  - `forced_explore_rate: 0.0`
  - `llm_valid_decision_rate: 1.0`

Interpretation:
- At very short horizon (`target_llm_calls=4`), disabling forced explore did not collapse loop validity.
- At the same short horizon, value/trade/mint downstream metrics remain near zero and are not emergence-informative.

Subscription multiplier sweep (same seed/target, reduced mode):
- `0.5`: `logs/phase1_diag_mult_0p5_opus_s100_t4_1771792381_summary.json` (`llm_cost: 0.007545`)
- `1.0`: `logs/phase1_diag_mult_1_opus_s100_t4_1771792432_summary.json` (`llm_cost: 0.01509`)
- `2.0`: `logs/phase1_diag_mult_2_opus_s100_t4_1771792480_summary.json` (`llm_cost: 0.03018`)
- `4.0`: `logs/phase1_diag_mult_4_opus_s100_t4_1771792524_summary.json` (`llm_cost: 0.06036`)

Interpretation:
- Accounting sensitivity is monotonic as expected (budget charge responds linearly to multiplier).
- Behavioral substitution signal is weak at this short horizon; longer call budgets are required.

### 12.2C Longer-horizon anchor comparison (2026-02-22)

All runs used the same seed and horizon (`seed_base=100`, `target_llm_calls=20`) on `claude-code/opus`.

Baseline:
- `logs/phase1_anchor_baseline_opus_s100_t20_1771793543_summary.json`
- `llm_valid_decision_rate: 0.9545`
- `forced_explore_rate: 0.0455`
- `loop_action_entropy_bits: 2.313`
- `cross_transfer_amount: 12.0`
- `mint_submissions: 4.0`
- KPI lock: pass

Reduced:
- `logs/phase1_anchor_reduced_opus_s100_t20_1771792630_summary.json`
- `llm_valid_decision_rate: 0.9091`
- `forced_explore_rate: 0.0909`
- `loop_action_entropy_bits: 2.313`
- `cross_transfer_amount: 9.0`
- `mint_submissions: 4.0`
- KPI lock: pass

Off:
- `logs/phase1_anchor_off_opus_s100_t20_1771793868_summary.json`
- `llm_valid_decision_rate: 0.9545`
- `forced_explore_rate: 0.0`
- `fallback_rate: 0.0455`
- `recovery_fallback_rate: 0.0455`
- `loop_action_entropy_bits: 2.219`
- `cross_transfer_amount: 9.0`
- `mint_submissions: 1.0`
- KPI lock: fail (mint floor)

Interpretation:
- For this seed/horizon, forced exploration is not required for liveness or LLM engagement.
- Turning forced-explore fully off reduced mint throughput enough to fail the current KPI lock.
- A reduced/baseline mode currently preserves higher mint pressure while still keeping policy injection relatively low.
- Value-weighted market quality remains weak across all three (`cross_paid_consumption_amount: 0`, `mint_downstream_value: 0`), so current emergence signal is still activity-weighted rather than downstream-value-weighted.

### 12.2D Post-patch paid-consumption calibration (2026-02-22)

Patch applied in loop policy:
- prioritize affordable priced cross-principal read targets before free artifacts
- auto-set `read_price=1` for non-scratch loop `write_artifact` decisions when price is omitted

Validation run:
- `logs/phase1_postpatch_baseline_opus_s100_t8_1771803737_summary.json`
- `cross_paid_consumption_amount: 1.0`
- `cross_paid_consumption_events: 1.0`
- `reuse_weighted_artifact_value_total: 1.693147`

Long-horizon post-patch anchor (reduced):
- `logs/phase1_postpatch_anchor_reduced_opus_s100_t20_1771803925_summary.json`
- `cross_paid_consumption_amount: 1.0`
- `cross_paid_consumption_events: 1.0`
- `cross_transfer_amount: 9.0`
- `mint_submissions: 3.0`
- KPI lock: pass

Interpretation:
- Paid downstream consumption is now measurable in the main horizon class (`t20`), not just short diagnostics.
- Mint downstream value is still zero in this seed/horizon, so settlement-to-reuse economics are improved but not yet strong.

### 12.2E Closeout matrix + multiplier sweep (2026-02-23)

Operational note:
- DeepSeek remained unavailable in this environment due OpenRouter key-limit preflight failure (`403 key limit exceeded`).
- Closeout matrix was therefore executed on `claude-code/opus` with matched seed and call target.

New matrix CLI support:
- `scarcity_matrix` now accepts `--subscription-estimated-cost-multiplier` so multiplier sweeps no longer need temporary config files.

Commands used (single-run quick closeout profile):
- Baseline/reduced/off:
  - `logs/phase1_closeout3_baseline_opus_t10_r1_1771805660_summary.json`
  - `logs/phase1_closeout3_reduced_opus_t10_r1_1771805891_summary.json`
  - `logs/phase1_closeout3_off_opus_t10_r1_1771806030_summary.json`
- Multiplier sweep (`reduced`, `multiplier in {0.5,1,2,4}`):
  - `logs/phase1_closeout3_mult_0p5_opus_t10_r1_1771806174_summary.json`
  - `logs/phase1_closeout3_mult_1_opus_t10_r1_1771806301_summary.json`
  - `logs/phase1_closeout3_mult_2_opus_t10_r1_1771806446_summary.json`
  - `logs/phase1_closeout3_mult_4_opus_t10_r1_1771806606_summary.json`

Quick comparison (mean metrics):
- Baseline: `llm_cost=0.041061`, `forced_explore_rate=0.1`, `cross_paid_consumption_amount=0`, `mint_submissions=0`, KPI lock fail.
- Reduced: `llm_cost=0.040707`, `forced_explore_rate=0.2`, `cross_paid_consumption_amount=0`, `mint_submissions=0`, KPI lock fail.
- Off: `llm_cost=0.04017`, `forced_explore_rate=0.0`, `cross_paid_consumption_amount=2.0`, `cross_paid_consumption_events=2.0`, KPI lock fail.
- Multiplier 0.5: `llm_cost=0.020367`, KPI lock fail.
- Multiplier 1.0: `llm_cost=0.04071`, KPI lock fail.
- Multiplier 2.0: `llm_cost=0.081474`, KPI lock fail.
- Multiplier 4.0: `llm_cost=0.162948`, KPI lock fail.

Interpretation:
- Subscription charging is monotonic and approximately linear versus multiplier in this matched-seed quick profile.
- Short-horizon (`target_llm_calls=10`) runs are useful for instrumentation sanity and accounting monotonicity checks.
- These runs are not sufficient for emergence/KPI-lock claims (all failed mint/entropy/transfer floors by design at this short horizon).
- Use longer horizons (`target_llm_calls >= 20`, preferably runs >= 3 per condition) for emergence conclusions.

### 12.2F Medium matched-seed suite comparison (2026-02-23)

Completed suites (all conditions, all seeds):
- Default prompt:
  - `logs/phase1_suite_phase1_opus_default_med_20260223_suite.json`
- Prompt variant (`config/prompts/loop_prompt_variant.txt`):
  - `logs/phase1_suite_phase1_opus_prompt_variant_med_20260223_suite.json`

Shared setup:
- `model=claude-code/opus`
- `runs=5`
- `duration=420`
- `target_llm_calls=16`
- seeds `8100..8104`
- each condition gate-passed with `runs_included_in_aggregate=5`

Default prompt means:
- Baseline:
  - `llm_valid_decision_rate: 0.90394`
  - `forced_explore_rate: 0.08356`
  - `loop_action_entropy_bits: 2.1048`
  - `cross_paid_consumption_amount: 0.8`
  - `cross_transfer_amount: 7.4`
  - `reuse_weighted_artifact_value_total: 1.35452`
- Reduced:
  - `llm_valid_decision_rate: 0.85`
  - `forced_explore_rate: 0.125`
  - `cross_paid_consumption_amount: 1.4`
  - `cross_transfer_amount: 5.4`
  - `reuse_weighted_artifact_value_total: 2.69478`
- Off:
  - `llm_valid_decision_rate: 1.0`
  - `forced_explore_rate: 0.0`
  - `loop_action_entropy_bits: 1.4252`
  - `cross_paid_consumption_amount: 3.4`
  - `cross_transfer_amount: 0.4`
  - `reuse_weighted_artifact_value_total: 7.83614`

Prompt-variant deltas versus default (prompt minus default):
- Baseline:
  - `llm_valid_decision_rate: -0.0796`
  - `forced_explore_rate: +0.0796`
  - `cross_paid_consumption_amount: +0.6`
  - `cross_transfer_amount: -0.8`
  - `reuse_weighted_artifact_value_total: +1.17807`
- Reduced:
  - `llm_valid_decision_rate: +0.0125`
  - `forced_explore_rate: -0.05`
  - `cross_paid_consumption_amount: +2.0`
  - `cross_transfer_amount: -1.8`
  - `reuse_weighted_artifact_value_total: +4.79615`
- Off:
  - `llm_valid_decision_rate: -0.0375`
  - `forced_explore_rate: 0.0`
  - `loop_action_entropy_bits: +0.4162`
  - `cross_paid_consumption_amount: +0.0`
  - `cross_transfer_amount: +2.2`
  - `reuse_weighted_artifact_value_total: -0.253702`

Operational recommendation from this comparison:
- Primary track for emergence diagnosis:
  - prompt variant + `off`
- Secondary fallback/liveness track:
  - prompt variant + `reduced`
- Do not use prompt-variant baseline as primary evidence:
  - improved value metrics but increased policy injection in matched seeds.

Current uncertainties (documented, proceed anyway):
- Value appears to be flowing through priced consumption more than direct transfers in off-mode; this may be true adaptation or metric-channel substitution.
- Mint remains weak and should not be used as a primary emergence criterion yet.
- Off-mode has seed-level variance in reuse-value deltas; keep matched-seed confirmatory runs (`n>=10`) as next validation step.

### 12.2G Experiment workflow reliability fixes (2026-02-23)

Applied while confirmatory runs were in progress:

1. `scarcity_matrix` now flushes `run_ids.txt` and matrix JSONL after every replicate write so long-run progress is observable before process exit.
2. `scarcity_matrix` now emits a compact per-run completion line with key signals (`llm_calls`, `forced_explore_rate`, `cross_paid_consumption_amount`).
3. `phase1_suite` now launches matrix children with unbuffered Python (`-u`) and flushes status prints.
4. AE3 syscall path now passes `max_retries=0` explicitly for agent-SDK models (`claude-code/*`, `codex/*`, `openai-agents/*`) to match side-effect-safe semantics and suppress repeated retry-disabled warning spam in long driver logs.
5. Added `analysis.matrix_progress` CLI to summarize partial matrix JSONL during active runs (completed replicate count + rolling aggregate + last-run signals).

Experiment backbone scope decision:

1. Primary system remains `llm_client` experiments (`start_run/log_item/finish_run`, `compare_cohorts`, gate-policy evaluation) because it natively models scenario/condition/seed/replicate cohorts.
2. `prompt_eval` is explicitly deferred as primary AE3 infrastructure until an external-runner adapter exists that maps simulation replicates into prompt-eval trial semantics without losing cohort metadata.

### 12.3 Summarize a run

```bash
PYTHONPATH=src python -m agent_ecology3.analysis.emergence_report \
  --events logs \
  --run-id run_YYYYMMDD_HHMMSS \
  --pretty
```

### 12.4 Log summary into llm_client experiment registry

```bash
PYTHONPATH=src python -m agent_ecology3.analysis.emergence_report \
  --events logs \
  --run-id run_YYYYMMDD_HHMMSS \
  --log-experiment \
  --llm-client-repo /home/brian/projects/llm_client \
  --pretty
```

## 13. Current working tree state that may matter

As of this handoff, notable local changes include:
- Subscription budget policy and tests.
- Role/prompt nudges for market behavior.
- MCP bridge files under `src/agent_ecology3/mcp/`.
- `config/config.tight_scarcity.yaml` present locally.

Potentially unrelated local edits also exist (dependency/config adjustments) and should be reviewed before release decisions.

## 14. What we need ChatGPT to do

We want critique, not agreement. We want concrete mechanism advice and experiment designs that can falsify assumptions.

Please advise on:

1. Mechanism design for scarce-resource allocation and contracting
- How to keep "allocation then contract" coherent while still allowing useful bidding where warranted.
- Whether mint bids should burn, redistribute, or split.

2. Emergence-valid evaluation design
- Metrics and qualitative checks that better distinguish true strategic adaptation from scripted or noisy behavior.
- Minimal experiment set that can falsify "emergence is real".

3. Cognitive architecture upgrades that preserve simplicity
- Highest-leverage changes to improve planning, memory usage, and mistake recovery without heavy framework bloat.
- How to deepen specialization so agents have real comparative advantage.

4. Subscription-mode scarcity calibration
- How to calibrate `subscription_estimated_cost_multiplier` so budget pressure is realistic across models.
- How to avoid either trivial non-binding budgets or overly punitive starvation.

5. Avoiding model hobbling
- Identify where loop gating/fallbacks might suppress strong models.
- Recommend minimal guardrails that preserve safety while maximizing strategic agency.

## 15. Non-negotiables for any proposed plan

1. Do not replace emergence with hand-authored scripts that force target behavior.
2. Keep contract-based rights as the central access model.
3. Keep accounting semantics explicit and auditable.
4. Prefer simple, testable increments over architecture sprawl.
5. Ensure proposals can be evaluated with reproducible runs and clear failure criteria.

---

If you (ChatGPT) propose a new plan, structure it as:
1. Hypothesis
2. Minimal code/config changes
3. Expected behavioral change
4. Falsification test
5. Rollback criteria
