# Phase 1.9F Gap Register

Phase 1.9F classifies gaps discovered during the operational benchmark and closure audit.

## BLOCKER

None unresolved.

No critical orphan provenance, false COMPLETE, false corroboration inflation, canonical boundary bypass, resume duplication, or material narrative validation-state misrepresentation was found in the final benchmark run.

## IMPORTANT

### Duplicate Registered Source Fetch Consumption

- Finding: if repeated acquisition calls registered or returned the same `Source`, the loop could carry duplicate source IDs into content fetching.
- Severity: IMPORTANT.
- Impact: duplicated fetches could waste content budget and distort operational metrics.
- Fix: deduplicate registered source IDs before the loop enters content fetch.
- Regression: `tests/test_research_loop.py::test_loop_deduplicates_registered_sources_before_fetching`.
- Status: resolved.

### Benchmark Claim Text Rejected As Action Language

- Finding: the first supplied-material benchmark run reached narrative synthesis but report validation rejected findings containing action-shaped words such as `trade`.
- Severity: IMPORTANT.
- Impact: the report would have violated the no-recommendation/no-financial-advice boundary if the guard had not stopped it.
- Fix: revised benchmark materials to state operational observations without action/recommendation wording.
- Regression: `tests/test_phase_1_9f_operational_benchmark.py::test_phase_1_9f_operational_benchmark`.
- Status: resolved.

## DEFERRED

- Live external research remains unverified without usable acquisition and reasoning credentials.
- Source-to-plan relevance pruning is simple; Phase 1.9F accepted the bounded 113-provider-call supplied-material run because it stayed within budget and completed quickly.
- Resume remains limited to explicit waiting gates.
- No operator UI exists for reviewing loop executions, candidates, or reports.
- Token and cost accounting remains zero/unknown for deterministic fake and supplied-material providers.
- Browser automation, PDF/OCR/media ingestion, embeddings, graph/vector DBs, recommendation logic, trading/exchange execution, and scheduled/background research remain out of scope.

## Final Gap Decision

`PHASE_1_9_READY_TO_CLOSE`
