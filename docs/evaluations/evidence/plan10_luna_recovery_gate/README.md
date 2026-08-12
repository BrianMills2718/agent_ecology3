# Plan 10 Luna Recovery Gate Evidence

This directory retains the provider-free Slice A route inventory. It contains
no provider response, credential, live Luna call, Evaluation 07 mutation, or
Evaluation 08 evidence.

## Current result

`slice_a_preflight.json` is `blocked` with
`blocker_code=intrinsic_codex_events_not_public` at shared-client revision
`e068430c991fd460c73d7f4faf5c92ee393b8a66`.

The passing parts of the inventory are:

- exact model `codex/gpt-5.6-luna`, medium effort, direct CLI transport;
- read-only newly empty decision workspace and `approval_policy=never`;
- isolated Codex home with no inherited MCP server;
- exact provider schema sent with `--output-schema`, six closed action
  branches, and schema digest
  `4f8344df4e01d3f7adf1287ffe794edeb2552f94e8d8268558d3cc102be5d2d2`;
- no `tools` or `mcp_servers` argument on the structured shared-client call;
  and
- zero retries and zero fallback models.

The blocking probe feeds the reviewed shared adapter synthetic completed items
of types `command_execution`, `file_change`, `web_search`, and
`mcp_tool_call`. Only the MCP item survives into the public result. The public
raw response carries a transport/session summary, so AE3 cannot distinguish
zero intrinsic tool executions from hidden intrinsic tool executions.

## Reproduce without a provider call

```bash
PYTHONPATH=src:/path/to/llm_client python -m \
  agent_ecology3.analysis.luna_recovery_gate \
  --config config/config.luna_recovery_gate.yaml \
  --llm-client-repo /path/to/llm_client \
  --output docs/evaluations/evidence/plan10_luna_recovery_gate/slice_a_preflight.json
```

Exit code `2` is the expected blocked result until the shared client exposes
intrinsic Codex event custody. Do not change the test to expect success without
that public capability.
