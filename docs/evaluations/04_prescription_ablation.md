# Evaluation 04: Prescriptive Cognition Ablation

**Preregistered:** 2026-08-11 (before any evaluation model call)
**Stage:** Exploratory proof of concept
**Decision owner:** Brian Mills
**Lifecycle effect:** None; AE2 and AE3 remain separately active

## Claim and decision

Falsifiable claim: under the same scarce-resource kernel and legal action
surface, AE3's minimally prescribed cognition condition can produce an
artifact through an `llm_valid` action that another principal later pays to
consume. The claim passes this probe when that happens in at least two of three
minimal-condition runs.

Decision after this probe:

- **Continue** to a larger component-ablation study if the positive and
  negative controls pass and minimal passes at least 2/3 runs.
- **Revise** the minimal scaffold or horizon if controls pass and minimal
  passes exactly 1/3 runs.
- **Stop/rethink** the claim that current AE3 evidence is independent of its
  prescriptions if controls pass and minimal passes 0/3 runs.
- **Inconclusive** if either control fails or more than one paid run is invalid.

This probe does not establish emergence, generalize beyond the selected model
and kernel, identify which removed instruction caused an effect, validate
minting as a value signal, or authorize an AE2/AE3 lifecycle change.

## Unit, population, and conditions

The experimental unit is one isolated AE3 simulation with four principals.
The target population is AE3 runs using the repository's default
`minimax/minimax-m3` route, the frozen ablation config, and the current kernel.
Seeds `12100`, `12101`, and `12102` are matched across conditions. They control
deterministic loop helper choices; provider sampling may remain stochastic.

| Condition | LLM | Cognition | Prompt | Purpose |
|---|---:|---|---|---|
| prescribed | on | assigned roles + objective cycle | `config/prompts/loop_prompt_variant.txt` | Positive assay control |
| minimal | on | no roles or objective cycle | `config/prompts/loop_prompt_minimal.txt` | Treatment |
| llm_off | off | prescribed | no model call | Negative attribution control |

All paid runs use 16 successful LLM syscalls as the normalization target and,
after the preregistered infrastructure amendment below, 900 seconds as the
safety cap. LLM-off runs use 8 seconds. Forced exploration
is off. The action gate and recent-feedback state remain on in both paid
conditions because they are validity/safety infrastructure, not behavioral
targets.

## Outcomes and thresholds

Primary per-run outcome:

```text
llm_valid_downstream_value > 0
```

This is scrip paid by a different principal to read or invoke an artifact whose
creation was attributed to `decision_origin=llm_valid`. The aggregation unit is
the run; repeated purchases within one run do not create extra replicates.

Secondary descriptive outcomes are total cross-paid consumption,
LLM-valid-decision rate, fallback rate, action entropy, reuse-weighted artifact
value, per-origin value, and final resource balances. They cannot rescue a
failed primary outcome.

Control and validity rules:

- Positive control passes when at least 2/3 prescribed runs have positive
  primary outcome.
- Negative control passes only when every LLM-off run has exactly zero
  `llm_valid` decisions and zero LLM-valid downstream value. Other
  fallback-origin activity is expected and is not evidence for the claim.
- Each paid run requires 16 successful syscalls, at least 12 LLM-valid
  decisions, and `llm_valid_decision_rate >= 0.75`.
- A paid run failing those thresholds is invalid. One invalid run may be
  reported but makes any 2/3 result provisional; more than one invalid paid run
  makes the evaluation inconclusive.
- Any forced-explore event, trace-link failure, prompt/config mismatch, or
  evidence-bundle hash failure invalidates the affected run.

No post-hoc exclusions or threshold changes are allowed. Unexpected behavior
is retained and described.

## Call and spend boundary

The maximum planned successful LLM syscalls are 97: one positive-control
preflight plus `2 conditions * 3 runs * 16 calls`. Provider retries are zero.
Each preflight/paid simulation has a shared `llm_client` root-trace budget of
USD 0.25, for a configured aggregate ceiling of USD 1.75 across the seven paid
trace scopes. The client also reserves USD 0.01 before each dispatch and, after
the infrastructure amendment below, caps output at 1,024 tokens. Stop before
the matrices if preflight fails or reports a
projected aggregate cost above USD 1.75. Stop a condition on a provider budget
error rather than silently changing model, prompt, retries, or sample size.

## Evidence contract

Before interpretation, preserve:

- the exact Git commit, dirty-state check, model, condition, seed, and run ID;
- the effective config and both prompt files with SHA-256 hashes;
- raw AE3 event JSONL, per-condition matrix JSONL/summary/run-ID files, and
  SHA-256 manifest;
- every AE3 syscall/decision trace ID and a receipt proving the matching
  `llm_client` record retains rendered messages and raw response content;
- per-run primary outcomes, invalidity reasons, control verdicts, and the
  frozen decision classification above.

Results will be appended below only after the implementation and focused/full
tests pass.

## Infrastructure amendment before the decisive run

The first prescribed-condition attempt (`run_20260812_005820`, seed `12100`)
was retained as an invalid pilot and is excluded from every control and
treatment count. Twelve serial provider attempts consumed 263.63 runtime
seconds: ten succeeded, one timed out at 60 seconds, and one returned an empty
response. Because synchronous provider calls block AE3's event loop, the
240-second monitor could check its stop conditions only between calls. The run
therefore ended below the frozen requirements at 10/16 successful syscalls and
9/12 LLM-valid decisions. It nevertheless recorded 1.0 unit of
LLM-valid downstream paid value; that observed outcome does not count.

Before any valid control or treatment result, the safety cap was increased to
900 seconds and `simulation.max_runtime_seconds` to 960. The hypothesis,
conditions, prompts, model, seeds, sample size, successful-call target, outcome
definition, pass thresholds, retry count, and spend caps are unchanged. The
matrix fail policy was also repaired to persist an invalid run record before
raising. These are infrastructure corrections, not outcome-threshold changes.

The first post-horizon control attempt (`run_20260812_011048`, seed `12100`)
reached 16 successful calls and 15 LLM-valid decisions, but six additional
provider calls exhausted the 512-token output allowance before returning any
action. Those fallback decisions reduced the LLM-valid-decision rate to 0.6818,
below the frozen 0.75 threshold. The run is retained as the evaluation's one
allowed invalid paid run; its 1.0 unit of LLM-valid downstream value does not
count. The output cap was raised to 1,024 before continuing, while the USD 0.25
trace cap, zero retries, prompts, model, seeds, sample size, call target, and
all outcome thresholds remain unchanged. The invalid pilots plus preflight
cost USD 0.0238663; reserving the full USD 0.25 cap for each of the six
remaining condition runs keeps worst-case aggregate spend below USD 1.75.

Because one paid run is invalid, even a passing 2/3 result is provisional under
the frozen rule. Any additional invalid paid run makes Evaluation 04
inconclusive; the matrix will retain and drop invalid rows rather than lose the
remaining matched evidence.

## Results

Not run yet.
