# Plan 10 Luna Recovery Gate Evidence

This directory retains the provider-free Slice A route inventory. It contains
no provider response, credential, live Luna call, Evaluation 07 mutation, or
Evaluation 08 evidence.

## Current result

`slice_a_preflight.json` is `pass` with no blocker at accepted shared-client
revision `286715784f1d535d6dfcd2c867ca678d666e27d5`. The public event contract
it consumes was implemented in `llm_client` merge
`63f471347f2f1e18b37cf82d50b5546336b6a5e1`.

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

The public-contract probe feeds the reviewed shared adapter synthetic completed
items of types `command_execution`, `file_change`, `web_search`, and
`mcp_tool_call`. All four remain ordered in `result.codex_events`; the existing
`result.tool_calls` compatibility projection still contains only the MCP item.
AE3 can therefore inspect the intrinsic event stream without installing or
invoking an MCP server.

## Reproduce without a provider call

```bash
PYTHONPATH=src:/path/to/llm_client python -m \
  agent_ecology3.analysis.luna_recovery_gate \
  --config config/config.luna_recovery_gate.yaml \
  --llm-client-repo /path/to/llm_client \
  --output docs/evaluations/evidence/plan10_luna_recovery_gate/slice_a_preflight.json
```

Exit code `0` is expected at the reviewed shared-client revision. This remains
a synthetic, provider-free contract check; it does not certify a live Luna
turn, recovery behavior, or detached worker operation.
