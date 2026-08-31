# Phase 1.9F Operational Research Benchmark

## Question

Is cross-exchange spot arbitrage practically viable in 2026 for a retail operator with approximately USD 5,000 in capital after realistic trading fees, executable spreads, slippage, transfer constraints, capital fragmentation, rebalancing, API limitations, and operational risk?

This benchmark does not provide personalized financial advice, recommendations, or execution instructions.

## Benchmark Mode

`SUPPLIED_MATERIAL_OPERATIONAL_BENCHMARK`

Live external research was not run because usable live acquisition plus reasoning credentials are not assumed in the local test environment. Live 2026 research remains explicitly unverified.

## Execution

- execution date: 2026-08-31
- method/version: `controlled-research-loop-1.9e`
- runner: `benchmarks/phase-1.9f/run_operational_benchmark.py`
- supplied material: `benchmarks/phase-1.9f/operational-materials.json`
- result summary: `benchmarks/phase-1.9f/benchmark-result-summary.json`
- regression test: `tests/test_phase_1_9f_operational_benchmark.py`

## Providers / Models

- planning: `phase-1.9f-supplied-planner/supplied-material-planner-v1`
- acquisition: `phase-1.9f-supplied-acquisition`
- content: `phase-1.9f-supplied-fetch`
- Evidence: `phase-1.9f-supplied-evidence/supplied-material-evidence-v1`
- Claims: `phase-1.9f-supplied-claims/supplied-material-claim-v1`
- synthesis: `fake/fake-narrative-synthesis-v1`

The benchmark-local providers implement Darwin provider protocols and feed supplied material into the real `ResearchLoopController`. They do not bypass canonical services.

## Budgets

- max iterations: 2
- max searches: 10
- max sources: 20
- max fetched sources: 10
- max segments: 20
- max Evidence candidates: 20
- max accepted Evidence: 10
- max Claim candidates: 10
- max accepted Claims: 10
- max provider calls: 130
- max runtime seconds: 90
- max tokens/cost: not configured for supplied-material mode

## Research Plan

The plan created 10 required plan items:

1. trading fee economics
2. executable spread/opportunity size
3. liquidity/slippage
4. deposit/withdrawal costs
5. transfer/deposit timing
6. pre-funding / capital fragmentation
7. rebalancing costs
8. API/execution constraints
9. operational/counterparty risks
10. realistic net viability conditions

All 10 required plan items were satisfied by canonical Evidence created through accepted Evidence candidates.

## Operational Metrics

Planning:

- plan items: 10
- required items: 10
- satisfied items: 10
- warnings: supplied-material benchmark and no-advice limitations only

Acquisition:

- searches: 10
- persisted queries: 10
- source candidates: 10
- registered Sources: 10
- duplicates/failures: 0 observed in the final benchmark

Content:

- fetch attempts: 10
- successful snapshots: 10
- unsupported content: 0
- fetch failures: 0
- segments: 10

Evidence:

- candidates: 10
- valid grounded: 10
- rejected grounding: 0
- accepted: 10
- snapshot/segment provenance complete: true

Claims:

- candidates: 10
- rejected: 0
- accepted: 10
- ClaimEvidence links: 10
- ClaimEvidence completeness: true

Validation:

- `SUPPORTED`: 10
- `UNASSESSED`: 0
- `INSUFFICIENT_EVIDENCE`: 0
- `CORROBORATED`: 0
- `CONTESTED`: 0
- `CONTRADICTED`: 0
- `HUMAN_REVIEW_PENDING`: 0
- `HUMAN_VALIDATED`: 0

Loop:

- iterations: 1
- stage transitions: 8
- events: 165
- provider calls: 113 / 130
- runtime: about 0.57 seconds in the recorded local run
- stop reason: `SUCCESS_COMPLETE`
- completion assessment: `COMPLETE`

Synthesis:

- narrative findings: 13
- contradictions: 0
- evidence gaps: 0
- report published: true
- report artifact verified during benchmark execution: true

## Provenance Audit

Representative chain verified:

```text
Report finding
-> canonical Claim
-> ClaimEvidence
-> Evidence
-> Source
```

Snapshot-derived Evidence chain verified:

```text
Evidence
-> SourceContentSegment
-> SourceContentSnapshot
-> raw/normalized artifact metadata
-> Source
```

No critical orphan provenance was found.

## Source-Independence Audit

Publisher distribution:

- Supplied Exchange API Documentation: 1
- Supplied Exchange Fee Documentation: 1
- Supplied Exchange Funding Documentation: 2
- Supplied Market Microstructure Notes: 2
- Supplied Operational Risk Notes: 1
- Supplied Retail Operations Analysis: 2
- Supplied Retail Viability Analysis: 1

No Claim was elevated to `CORROBORATED`; all accepted Claims validated as `SUPPORTED`. The benchmark therefore did not inflate multiple supplied materials from related publishers into independent corroboration.

## Auto-Grounded Audit

- Evidence exact grounding remained enforced by candidate acceptance.
- Accepted Evidence candidates used `AUTO_ACCEPTED` mode.
- Accepted Claims used `AUTO_ACCEPTED` mode and linked to canonical Evidence.
- Claim acceptance did not imply validation; `ClaimValidationService` produced the final `SUPPORTED` states.
- Narrative synthesis did not create canonical Evidence, Claims, validation records, or Conclusions.

## Stop / Resume Audit

The operational benchmark completed without hitting a manual gate. Separate deterministic regression tests cover:

- budget stop
- no usable source/no canonical Evidence/no canonical Claims
- Evidence approval gate
- Claim approval gate
- synthesis publication gate
- resume without duplicate canonical Evidence/Claims
- human review stop

## Report Quality Audit

The first benchmark run was stopped by narrative validation because benchmark claim text contained action-shaped trading language. The supplied materials were revised to observational language, and the final run produced a traceable report without prohibited recommendation wording.

Report integrity outranked polish. The report is useful as a process artifact over supplied material, but it is not live financial research.

## Gap Register

See `docs/benchmarks/phase-1.9f-gap-register.md`.

## Hardening Fixes

- Deduplicated registered source IDs before content fetching in `ResearchLoopController`.
- Added `test_loop_deduplicates_registered_sources_before_fetching`.
- Added executable 1.9F benchmark regression.
- Revised benchmark material after narrative validation rejected action-shaped wording.

## Final Acceptance

`PHASE_1_9_READY_TO_CLOSE`
