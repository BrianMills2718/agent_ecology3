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

Verify: `sha256sum -c SHA256SUMS`. Restore: `tar -xzf <bundle> -C ~/.local/state/agent_ecology3/`.
