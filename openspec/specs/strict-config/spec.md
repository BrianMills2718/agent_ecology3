# strict-config Specification

## Purpose
Characterize the existing strict configuration loader in `src/agent_ecology3/config.py`: it rejects what it does not recognise instead of guessing. This documents behavior that already worked; it adds no new requirement. The rest of the repository is not covered.

## Requirements

### Requirement: Unknown keys rejected

The configuration models SHALL reject any key they do not declare.

Source: inferred by agent, 2026-11-17: restates the "Fail loud" design principle in AGENTS.md and the existing `StrictModel` (Brian, 2026-11-17: "option B is what i want").

#### Scenario: Unknown key

- **WHEN** a configuration contains a key no model declares
- **THEN** validation fails with a validation error

#### Scenario: Known keys only

- **WHEN** a configuration contains only declared keys
- **THEN** validation succeeds

### Requirement: Task bounty needs a task bank

The mint configuration SHALL refuse `mode: task_bounty` when no `task_bank_path` is given.

Source: inferred by agent, 2026-11-17: restates the existing `MintConfig` validator (Brian, 2026-11-17: "option B is what i want").

#### Scenario: Task bounty without a task bank

- **WHEN** a mint configuration sets `mode` to `task_bounty` and gives no `task_bank_path`
- **THEN** validation fails naming `task_bank_path`

### Requirement: Luna structured profile is exact

The LLM configuration SHALL refuse `decision_output_mode: luna_structured_v1` unless every field of the Plan 10 profile matches.

Source: inferred by agent, 2026-11-17: restates the existing `LLMConfig` validator (Brian, 2026-11-17: "option B is what i want").

#### Scenario: Partial Luna profile

- **WHEN** an LLM configuration selects `luna_structured_v1` with a default model other than `codex/gpt-6-luna`
- **THEN** validation fails with a message naming the mismatched field
