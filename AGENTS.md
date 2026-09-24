# agent_ecology3 - Project Context

---

## Quick Reference - Commands

### Session Start
```bash
make status              # Git status
```

### During Work
```bash
make test                # Run tests
make check               # All checks (test, mypy, doc-coupling)
```

### Finishing Work
```bash
make pr-ready            # Rebase + push
make pr                  # Create PR
make finish BRANCH=X PR=N  # Merge + cleanup
```

---

## Project Structure

```
agent_ecology3/
  src/                    # Source code
  tests/                  # Test suite
  docs/
    plans/                # Implementation plans
    adr/                  # Architecture Decision Records
  config/                 # Configuration files
  scripts/                # Utility scripts
```

---

## Workflow

### The Complete Cycle

```
1. START     -->  git checkout -b plan-N-description
       |
2. IMPLEMENT -->  Edit files, commit with [Plan #N] prefix
       |
3. VERIFY    -->  make test && make check
       |
4. SHIP      -->  make pr-ready && make pr && make finish BRANCH=X PR=N
```

### Commit Messages

```bash
[Plan #N] Description       # Links to plan
[Trivial] Fix typo          # For tiny changes (<20 lines)
```

---

## Key Rules

### Plans
- All significant work requires a plan in `docs/plans/NN_name.md`
- Use `[Trivial]` only for <20 lines, no src/ changes

### Process Awareness
- If you're doing something not covered by the meta-process (no pattern, no
  template, no convention), treat it as a signal:
  - Either the meta-process has a gap — record it in `meta-process/ISSUES.md`
  - Or you're deviating from process — stop and ask before continuing
- Don't silently invent new conventions. Make them explicit.

---

## Design Principles

1. **One authentic path** - Maintained LLM cognition uses the shared
   `llm_client`; principals, economy, artifacts, and custody remain AE3-owned.
2. **Fail loud** - An authentic run MUST stop and become invalid on transport,
   model, schema, decision-gate, or selected-action failure. It MUST NOT replace
   the failed decision with a local action, retry, fallback model, or synthetic
   success. Preserve the original error and trace/custody state.
3. **Fixtures are visibly non-authentic** - Deterministic substitutes are
   allowed only in explicitly provider-free tests or historical analysis. They
   cannot count as model-selected actions or support an authentic-run claim.
4. **Durable workers use durable paths** - A worker that may outlive a branch
   MUST NOT use a removable worktree as its current directory. Runtime status
   must distinguish attempted dispatch, provider-confirmed settlement, and
   locally applied action.
5. **Truth before polish** - Receipts and the dashboard must expose invalid
   custody and decision provenance; a fallback or failed model call is never a
   successful agent decision.

---

## Terminology

| Use | Not | Why |
|-----|-----|-----|
| `authentic run` | `live-ish run` | Requires real shared-client model custody and no substitute decisions |
| `provider-free fixture` | `authentic run` | Proves plumbing without claiming model behavior |
| `fallback action` | `agent decision` | A local substitute is not model-selected behavior |

---

## References

| Doc | Purpose |
|-----|---------|
| `README.md` | Full documentation |
| `docs/plans/AGENTS.md` | Plan index |
| `scripts/AGENTS.md` | Script reference |


## Multi-Agent Coordination

This repo uses worktree-based isolation for concurrent AI instances.

**Before starting work:**
1. Check existing claims: `python scripts/meta/worktree-coordination/check_claims.py --list`
2. Claim your work: `python scripts/meta/worktree-coordination/check_claims.py --claim --feature <name> --task "description"`
3. Create a worktree: `make worktree` (or `git worktree add worktrees/plan-N-desc`)
4. Work in the worktree, not the main directory

**Before committing:**
- Commits must use prefixes: `[Plan #N]`, `[Trivial]`, or `[Unplanned]`
- Release claims when done: `python scripts/meta/worktree-coordination/check_claims.py --release`

**Check for messages from other instances:**
`python scripts/meta/worktree-coordination/check_messages.py`
