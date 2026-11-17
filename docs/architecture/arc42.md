# Agent Ecology 3 architecture

The maintained system model is [the ODD description](../model/ODD.md) with its machine-readable twin [ae3_model.yaml](../model/ae3_model.yaml) and [trace.yaml](../model/trace.yaml); how the code is organized is in [IMPLEMENTATION_BASELINE](../IMPLEMENTATION_BASELINE.md). Goal and requirements: [GOAL.md](GOAL.md), [REQUIREMENTS.md](REQUIREMENTS.md). Those remain the authority; this page does not restate them.

[The import model](model.c4) is scoped to the configuration loader (`agent_ecology3.config`) and its one consumer checked here, the command line (`agent_ecology3.cli`). The rest of the code (world, analysis, dashboard) is described in the documents above and is not covered by an import contract yet.

The configuration capability is specified in [strict-config](../../openspec/specs/strict-config/spec.md).
