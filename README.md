# Agent Ecology 3

Agent Ecology 3 is a clean-room rewrite of `agent_ecology2` focused on:

- Clear kernel boundaries (`World`, `ActionExecutor`, `SafeExecutor`, `SimulationRunner`)
- Explicit resource accounting (scrip, llm_budget, disk quota, rolling rate limits)
- Contract-driven artifact access control
- Autonomous artifact loops (`has_loop=True`)
- JSONL-first observability with a minimal FastAPI dashboard

All six approved removals from AE2 are applied as AE3 design constraints:
- no compat-shim sprawl
- no duplicated authority surfaces
- no dashboard panel zoo
- no dormant subsystems in default boot path
- strict config schema (no backward-key aliasing behavior)

## Quick Start

```bash
cd /home/brian/projects/agent_ecology3
pip install -e .
cp .env.example .env
python run.py --duration 120
# or: agent-ecology3 --duration 120
```

## CLI

```bash
python run.py --config config/config.yaml
python run.py --duration 300 --agents 4
python run.py --dashboard
python run.py --dashboard-only
```

## Autonomous Loop Behavior

- Loop artifacts can call LLM when `llm.enable_bootstrap_loop_llm: true`.
- The parser accepts both canonical AE3 action JSON and common LLM variants (`action` + `parameters`) and normalizes to internal intents.
- Non-canonical `query_kernel` types are inferred to supported kernel queries to reduce invalid-action churn.

## Project Layout

```text
agent_ecology3/
  run.py
  config/config.yaml
  src/agent_ecology3/
    world/        # kernel primitives, ledger, contracts, executor
    simulation/   # autonomous loop runner
    dashboard/    # minimal API + lightweight status UI
  tests/
```

## Docs

- `docs/REWRITE_SCOPE.md` - keep/add/remove scope for the rebuild.
- `docs/REMOVAL_SEQUENCE.md` - ordered removal plan for review one item at a time.
- `docs/REMOVAL_01_RUNTIME_GOVERNANCE.md` - detailed review doc for removal #1.
- `docs/REMOVAL_02_COMPAT_SHIMS_DISPATCH.md` - detailed review doc for removal #2.
- `docs/REMOVAL_03_BOUNDARY_MERGE.md` - detailed review doc for removal #3.
- `docs/REMOVAL_04_DASHBOARD_SPRAWL.md` - detailed review doc for removal #4.
- `docs/REMOVAL_05_DORMANT_BOOT_SUBSYSTEMS.md` - detailed review doc for removal #5.
- `docs/REMOVAL_06_BACKWARD_CONFIG_COMPAT.md` - detailed review doc for removal #6.
- `docs/IMPLEMENTATION_BASELINE.md` - implemented AE3 baseline scope and validation record.
- `docs/RESOURCE_ACCOUNTING.md` - real vs pseudo accounting decision framework.
- `docs/ACCOUNTING_CONSTANTS.md` - accounting-sensitive numbers/flags with update triggers and source links.
