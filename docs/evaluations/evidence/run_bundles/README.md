# Run bundles

Durable copies of authentic run folders that roadmap claims cite. The live
originals stay in `~/.local/state/agent_ecology3/`; these bundles are the
recoverable record.

| Bundle | Cited by |
|---|---|
| `plan19_luna_live_economic_mvp_v1.tar.gz` | Plan 19, MVP canonical exemplar |
| `plan23_emergent_v2_run3.tar.gz` | Plan 23 candidate (closed as plumbing evidence) |
| `plan24_canary_v1.tar.gz` | Plan 24 Luna-low canary |
| `plan24_pair_1.tar.gz` | Plan 24 v1 pair 1 — invalid (artifact-type lowercasing defect) |
| `plan24_v2_pair_1.tar.gz`, `plan24_v2_pair_2.tar.gz`, `plan24_v2_pair_3.tar.gz` | Plan 24 valid matched pairs (each holds `trading/` and `solo/`) |
| `plan25_shakeout_run1.tar.gz` | Plan 25 4-agent scale shakeout |
| `plan25_resident_probe2.tar.gz` | Plan 25 first resident-agent probe (2 agents, 2 turns) |
| `plan25_resident_run1.tar.gz` | Plan 25 4-agent resident run (stopped at turn 10 by the Claude weekly limit) |
| `plan25_resident_codex_probe3.tar.gz` | Plan 25 resident Codex/Luna probe (agents/ excluded: holds kernel tokens) |
| `plan25_resident_codex_run1.tar.gz` | Plan 25 4-agent resident Codex/Luna run, 10 turns (agents/ excluded) |
| `plan25_resident_codex_run2.tar.gz` | Plan 25 8-agent resident Codex/Luna run, 20 turns (agents/ excluded) |
| `plan25_codex_shell_probe2.tar.gz` | Plan 25 probe: Codex agent tests its own code (Codex home excluded) |
| `plan25_codeflow_run1.tar.gz` | Plan 25 8-agent CodeFlowBench run (redacted: CodeFlowBench-derived task and solution text withheld because redistribution terms are unverified; agents/ excluded) |

Verify: `sha256sum -c SHA256SUMS`. Restore: `tar -xzf <bundle> -C ~/.local/state/agent_ecology3/`.
