# Scripts Directory

Two kinds of scripts live here. All support `--help`; run them through
`uv run python ...` so they use the project environment.

## Experiment scripts

| Script | Purpose |
|--------|---------|
| `run_recoverable_evaluation.py` | Start, serve, operate, and read-only `review` bounded recoverable runs (the dashboard workbench path) |
| `build_aes_pilot.py` | Plan 27: build the stubbed tinydb sandbox governed by AES (outside this repo), print its `aes status`, or run `--stub-check` / `--reference-check` in a throwaway copy |
| `export_prescription_ablation_evidence.py` | Export the frozen Evaluation 04 evidence from ignored runtime logs |

## Process scripts (`scripts/meta/`)

| Script | Purpose |
|--------|---------|
| `meta/check_plan_tests.py` | Verify/run plan test requirements |
| `meta/complete_plan.py` | Mark plan complete |
| `meta/sync_plan_status.py` | Check or sync plan status between plan files and the index |
| `meta/merge_pr.py` | Merge PRs via GitHub CLI |
| `meta/check_doc_coupling.py` | Verify docs were updated when coupled source changed |

```bash
uv run python scripts/meta/check_plan_tests.py --plan N   # Run tests for plan
uv run python scripts/meta/complete_plan.py --plan N      # Mark complete
uv run python scripts/meta/sync_plan_status.py --check    # Plan status consistency
uv run python scripts/meta/check_doc_coupling.py --suggest  # What docs to update
```

## Worktree coordination (`scripts/meta/worktree-coordination/`)

| Script | Purpose |
|--------|---------|
| `check_claims.py` | Manage active work claims |
| `meta_status.py` | Dashboard: claims, PRs, progress |
| `finish_pr.py` | Complete PR lifecycle: merge + cleanup |
| `safe_worktree_remove.py` | Safely remove worktrees |
| `check_messages.py` | Inter-instance messaging inbox |
| `send_message.py` | Send messages to other instances |

## Configuration

- `meta-process.yaml` (repo root) - meta-process settings
- `scripts/relationships.yaml` - doc-code couplings that `check_doc_coupling.py`
  reads by default
- `scripts/doc_coupling.yaml` - an older coupling map; the checker reads it
  only when `relationships.yaml` is absent or passed with `--config`, so its
  couplings are not enforced today
