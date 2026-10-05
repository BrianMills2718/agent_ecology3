# ADR 0002: Keep the AE3 kernel for the trading-vs-solo comparison

**Status:** Accepted (agent decision under Brian's 2026-10-05 delegation)
**Date:** 2026-10-05
**Plan:** [Plan 24](../plans/24_external_score_vs_solo.md), milestone M1

## Question

Can an existing framework run Plan 24's comparison (two agents, scarce call
budget, tasks scored by an automatic checker, trading on vs off, durable
receipts, dashboard review) with less work than extending AE3?

## What was checked (about one hour)

| Candidate | What it is | Fit for this comparison |
|---|---|---|
| Concordia (Google DeepMind) | Generative social simulation; an LLM "Game Master" resolves actions; has inventory/payoff components | Would need the task checker, priced artifact purchase, call caps, receipts and a review UI rebuilt on it. In-house review (`world-substrate/docs/research/competitive-landscape-2026-09.md`) already treats it as a complement, not a replacement |
| Magentic Marketplace (Microsoft Research, 2025) | Open-source two-sided market: assistant agents for consumers, service agents for businesses; studies welfare, search and bias | Shopping between fixed buyer and seller roles; no producer-to-producer trading on scored work. Roles are assigned, which is the FM-01 trap for this question |
| CoffeeBench (2026) | Multi-agent supply-chain economy with farmer/roaster/retailer roles maximising income | Roles and the value chain are prescribed by the designer (FM-01) |
| AgentSociety, SOTOPIA, Melting Pot, MultiAgentBench | Social-science scale, social-intelligence evaluation, MARL substrates, collaboration benchmarks | Different question: none measures whether voluntary trading beats a solo baseline on outside-scored work |
| Mesa | Generic agent-based modelling plumbing | Not evaluated in-house yet; adds nothing AE3's runner lacks for two agents |

## Decision

Keep AE3. It already has the parts that took Plans 10–23 to make trustworthy:
ledger, priced artifact purchase, hard call cap, fail-loud custody, durable
receipts, and the reopenable dashboard. Plan 24 M2 needs only a checker-backed
scorer behind the existing `MintScorer` seam and a trading-off action gate.
Porting to any candidate would mean rebuilding those parts first.

**Adopt rather than build** the tasks themselves: take them from an existing
coding benchmark with hidden tests (choice made in M2's bounded design), not a
hand-written bank.

## Wrong if

- M2's extension grows past roughly 600 authored lines, or needs a new runtime
  or UI. Then re-check Concordia's payoff components before continuing.
- A framework is found that already runs voluntary-trade vs solo on externally
  checked tasks. Then compare its effort to M3 before running pairs.

## Sources

- https://www.microsoft.com/en-us/research/blog/magentic-marketplace-an-open-source-simulation-environment-for-studying-agentic-markets/
- https://arxiv.org/pdf/2606.16613 (CoffeeBench)
- https://aclanthology.org/2025.acl-long.421/ (MultiAgentBench)
- `~/code/world-substrate/docs/research/competitive-landscape-2026-09.md`

## Addendum (2026-10-05): in-house option missed

This review checked outside frameworks only. It missed World Substrate
(`~/code/world-substrate`), Brian's own engine in which agents state intents
and installed mechanics decide consequences, with a world-agnostic living view,
replay and branching. Brian chose to use only its living view for now (an
adapter that emits its projection bundle). Running the economy on World
Substrate's engine remains unevaluated; consider it before growing AE3's own
kernel substantially for scale.
