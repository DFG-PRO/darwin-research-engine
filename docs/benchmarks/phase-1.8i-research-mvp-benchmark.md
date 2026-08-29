# Phase 1.8I Research MVP Benchmark

## Question

Is cross-exchange spot arbitrage still practically viable in 2026 for a retail operator with approximately USD 5,000 in capital, considering trading fees, spreads, slippage, liquidity, transfer/deposit/withdrawal constraints, execution latency, capital fragmentation, and rebalancing requirements?

## Execution Mode

`SUPPLIED_MATERIAL_BENCHMARK`

Execution date: 2026-08-29

No `.env` file was present. The configured external search provider was `fake`, and no Brave Search API key was configured. Live external acquisition was therefore not performed.

## Framing

Objective: assess whether realistic net arbitrage opportunities can remain after operational costs and constraints for a retail-scale operator.

Scope: operational/economic viability only. This benchmark does not produce personalized financial advice.

Out of scope: leverage, derivatives, HFT, tax optimization, jurisdiction-specific legal advice, automatic strategy execution, market-making, MEV, and personalized recommendations.

## Research Plan

Required categories:

1. Trading fee economics
2. Spread/opportunity size
3. Liquidity/slippage
4. Transfer/withdrawal costs
5. Transfer/deposit timing constraints
6. Pre-funding / capital fragmentation
7. Rebalancing requirements/cost
8. Execution/API constraints
9. Operational/counterparty risks
10. Net viability conditions

All 10 required items were satisfied by explicit evidence references in the supplied-material benchmark.

## Source Strategy

The benchmark used eight supplied source excerpts under `benchmarks/phase-1.8i/source-manifest.json`. Four were marked `primary_supplied`, two `high_authority_supplied`, one `supplied_analysis`, and one `derived_supplied`.

The derived source intentionally mirrors the fee source to test false corroboration prevention. It was not counted as an independent origin.

## Pipeline Executed

The runner exercised:

```text
Research Question -> Framing -> Research Plan -> Supplied Sources -> Source Registration
-> Content Fetch -> Snapshot -> Normalization -> Segmentation -> Explicit Evidence
-> Claim Construction -> Claim Validation -> Structured Synthesis -> Conclusion
-> Completion Assessment
```

Benchmark runner: `benchmarks/phase-1.8i/run_benchmark.py`

## Key Claims

Constructed Claims: 11

- fee-floor-not-independent
- net-cost-floor
- quoted-spread-not-profit
- withdrawal-fixed-costs
- timing-risk
- quick-transfer-contested
- capital-fragmentation
- rebalancing-cost
- api-execution-risk
- operational-counterparty-risk
- limited-venue-dependent-viability

Validation distribution:

- `SUPPORTED`: 8
- `CORROBORATED`: 2
- `CONTESTED`: 1
- `CONTRADICTED`: 0
- `INSUFFICIENT_EVIDENCE`: 0
- `HUMAN_REVIEW_PENDING`: 0
- `HUMAN_VALIDATED`: 0

## Contradictions

One natural supplied-material tension was preserved:

- Claim key: `quick-transfer-contested`
- State: `CONTESTED`
- Reason: one supplied excerpt supports quick network confirmation under normal conditions, while another supplied excerpt states deposits/withdrawals can be delayed or suspended by confirmation policy, maintenance, network conditions, or risk controls.

Darwin preserved both sides and surfaced the contradiction in structured synthesis.

## Conclusion

Benchmark conclusion: cross-exchange spot arbitrage for a USD 5,000 retail operator is structurally difficult and highly venue, pair, timing, and fee dependent after realistic trading, liquidity, transfer, and rebalancing costs.

This is a benchmark conclusion over supplied material only. It is not live financial research and not investment advice.

## Metrics

Research coverage:

- required plan items total: 10
- required items satisfied: 10
- coverage: 100%

Source quality/provenance:

- total Sources: 8
- primary supplied Sources: 4
- independent source origins: 7
- sources lacking meaningful date metadata: 1
- derived/republication Sources: 1

Evidence:

- Evidence count: 8
- snapshot-derived Evidence: 8
- manual/supplied Evidence: 0
- complete Source provenance: 8
- complete Snapshot/Segment provenance: 8

Claims:

- total Claims: 11
- supported: 8
- corroborated: 2
- contested: 1

Synthesis:

- unresolved contradictions: 1
- evidence gaps: 0
- conclusion warnings: `claim_has_unresolved_contradiction`, `conclusion_claim_has_unresolved_contradiction`
- completion assessment: `UNRESOLVED_CONTRADICTION`

Process:

- failed acquisitions: unknown/not applicable
- failed fetches: 0
- unsupported content: 0
- deduplicated Sources: 0
- repeated identical snapshots: 1
- provider usage/cost: unknown/not applicable

## Provenance Audit

Representative Claims were audited through:

```text
Claim -> ClaimEvidence -> Evidence -> Source
```

Snapshot-derived Evidence was audited through:

```text
Evidence -> SourceContentSnapshot -> SourceContentSegment -> artifact path/fingerprint
```

Conclusion traceability was audited through:

```text
Conclusion -> ConclusionClaim -> Claim
```

No benchmark-critical orphan Claims were found.

## Source-Independence Audit

The `fee-floor-not-independent` Claim used one original fee source and one mirrored/derived source. Darwin reported:

- validation state: `SUPPORTED`
- independent source count: 1

The mirrored source did not inflate the Claim to `CORROBORATED`.

## Completion-Gate Audit

Observed/verified completion states:

- best achievable supplied benchmark run: `UNRESOLVED_CONTRADICTION`
- missing required evidence: `NEEDS_EVIDENCE`
- contested critical claim: `UNRESOLVED_CONTRADICTION`
- human review pending: `HUMAN_REVIEW_REQUIRED`

No clearly incomplete run was observed being marked `COMPLETE`.

## Findings

BLOCKER: none unresolved.

IMPORTANT: none requiring code hardening.

DEFERRED:

- live acquisition remains unverified without provider credentials
- current exchange rules/fees require live primary-source acquisition in a later run
- semantic extraction, semantic contradiction detection, confidence scoring, and recommendations remain out of scope

## Research MVP Acceptance Decision

`PHASE_1_8_READY_TO_CLOSE`
