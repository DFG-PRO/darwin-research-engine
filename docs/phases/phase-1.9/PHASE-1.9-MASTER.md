# Phase 1.9 Master

## 1. Executive Summary

Phase 1.9 turns Darwin v0.1 from a supplied-material research foundation into a controlled operational research system. It adds planning proposals, assisted Evidence extraction, assisted Claim construction, narrative report synthesis, and a bounded synchronous research loop with persistent execution history.

Phase 1.9 does not make Darwin an unbounded autonomous agent. Automation remains constrained by explicit requests, provider boundaries, exact grounding, Evidence/Claim acceptance, deterministic validation, completion assessment, budgets, stop reasons, and audit events.

## 2. Phase Objective

The objective was to connect Darwin's traceable research data model to controlled provider-assisted workflows without weakening the source-of-truth hierarchy established in Phase 1.8.

## 3. Phase 1.8 Starting Baseline

Phase 1.8 provided:

- core ResearchRun, Source, Evidence, Claim, ClaimEvidence, and Conclusion models
- lifecycle persistence services
- deterministic claim validation and human review events
- supplied-material orchestration
- external acquisition audit records
- source content snapshots, artifacts, and segments
- explicit Evidence extraction
- caller-supplied Claim construction
- structured synthesis
- Phase 1.8I benchmark and closure docs

## 4. Final Phase 1.9 State

Darwin now supports:

- controlled research planning proposals
- approval into ResearchRun framing and plan items
- assisted Evidence candidate proposals
- exact-grounded Evidence acceptance
- assisted Claim candidate proposals
- Evidence-grounded Claim acceptance
- deterministic Claim validation after acceptance
- narrative synthesis proposals
- explicit Markdown report publication
- controlled synchronous research loop execution
- persistent loop events, counters, budgets, queries, stop reasons, and result links
- deterministic 1.9E and operational 1.9F benchmarks

## 5. Evolution 1.9A-F

- 1.9A: research planning proposal boundary.
- 1.9B: assisted Evidence extraction candidate boundary.
- 1.9C: assisted Claim construction candidate boundary.
- 1.9D: controlled narrative research synthesis and report publication.
- 1.9E: controlled research loop.
- 1.9F: operational benchmark, hardening, gap register, and closure.

## 6. Operational Research Architecture

The operational stack is a modular monolith. `ResearchOrchestrator` exposes workflow helpers. `ResearchLoopController` coordinates existing services in a bounded synchronous invocation:

```text
ResearchLoopRequest
-> ResearchPlanner
-> AcquisitionService
-> SourceContentService
-> AssistedEvidenceExtractionService
-> AssistedClaimConstructionService
-> ClaimValidationService
-> StructuredSynthesisService
-> NarrativeSynthesisService
-> ResearchLoopResult
```

Each service owns its canonical records and validation checks.

## 7. Planner

The planner creates structured proposals only. Proposals contain normalized question, objective, scope, assumptions, categories, source-type expectations, and plan-item proposals.

## 8. Planning Provenance / Approval

Planning proposals are append-only. Approval creates `ResearchRun`, `ResearchFraming`, and `ResearchPlanItem` records. Approval mode is persisted as manual or auto-approved.

## 9. Assisted Evidence Extraction

Assisted extraction receives bounded source segments and returns candidate spans. Candidates are not canonical Evidence.

## 10. Exact-Grounding Invariant

Evidence candidate acceptance reloads stored segment text and verifies offsets plus exact excerpt equality before creating canonical Evidence.

## 11. Evidence Acceptance

Accepted candidates link to canonical Evidence and record acceptance mode. Rejected and invalid-grounding candidates remain audit history.

## 12. Assisted Claim Construction

Claim construction providers receive canonical Evidence only and return structured Claim candidates with explicit Evidence roles.

## 13. Claim Acceptance

Claim candidate acceptance revalidates Evidence provenance and creates canonical Claim plus ClaimEvidence links. Acceptance does not imply support or truth.

## 14. Validation Boundary

`ClaimValidationService` remains authoritative. Provider output cannot set validation state, confidence, conclusion status, or completion assessment.

## 15. Narrative Synthesis

Narrative synthesis receives a bounded canonical context containing Claims, latest validation, Evidence, Sources, Conclusions, contradictions, gaps, and completion state.

## 16. Narrative != Knowledge

Narrative proposals organize and explain canonical state. They cannot create Evidence, Claims, validation, Conclusions, Sources, plan items, acquisition, or snapshots.

## 17. Report Publication / Artifacts

Publication is explicit. Darwin revalidates proposal grounding and completion fidelity, renders Markdown, writes below `DARWIN_ARTIFACT_ROOT`, and stores path, SHA-256, size, and report metadata.

## 18. Controlled Research Loop

The loop persists one `ResearchLoopExecution`, append-only `ResearchLoopEvent` rows, and bounded `ResearchLoopQuery` rows. It coordinates the stack without becoming a background worker.

## 19. Modes

- `MANUAL_GATE`: stop for operator Evidence, Claim, and publication actions.
- `AUTO_GROUNDED`: auto-accept only validated candidates through existing acceptance services.
- `DRY_RUN`: validate control path and persist execution/events without canonical research records.

## 20. State Machine

States include planning, acquiring, fetching content, extracting Evidence, waiting approvals, constructing Claims, validating, assessing completion, iterating, synthesizing, completion, budget stop, needs-evidence stop, contradiction stop, human-review stop, and failure.

## 21. Budgets

Budgets cover iterations, searches, source candidates/registrations, fetches, segments, Evidence candidates, accepted Evidence, Claim candidates, accepted Claims, provider calls, runtime, optional tokens, and optional cost.

## 22. Stop Conditions

Stop reasons are explicit: success, approval waits, no usable sources, no canonical Evidence, no canonical Claims, evidence needed with no budget, max iterations, unresolved contradiction, human review, provider failure, budget exhaustion, time budget exceeded, fatal integrity error, and dry-run completion.

## 23. Iteration Policy

Iterations are bounded. The loop may continue only when budget and completion policy allow. It does not recursively search forever.

## 24. Resume / Recovery

Supported resume points are Evidence approval, Claim approval, and synthesis publication waiting states. Completed canonical actions are not replayed blindly.

## 25. Observability / Events

Loop events are the authoritative audit trail for stage transitions, provider/service calls, budget counters, linked objects, warnings, errors, and stop reasons.

## 26. Transaction Boundaries

The loop is not one giant transaction. Prior durable canonical work may remain if a later stage stops. Execution state must reflect the real boundary reached.

## 27. Provider Architecture

Providers are protocol-bound. Live providers are optional; fake and supplied-material providers support deterministic tests and benchmarks.

## 28. Security / Prompt Injection

Source content and provider output are untrusted data. Providers cannot select arbitrary tools, filesystem paths, database queries, shell commands, network targets, or Darwin methods.

## 29. Source-Of-Truth Hierarchy

```text
Source / Snapshot / Segment
-> Evidence
-> Claim
-> Claim Validation
-> Conclusion
-> Narrative Synthesis
-> Report
```

Loop records are orchestration history, not canonical truth.

## 30. Full Provenance Chain

Report claims can be traced through narrative findings to canonical Claims, ClaimEvidence, Evidence, SourceContentSegment, SourceContentSnapshot, artifacts, and Sources.

## 31. Temporal Validity

Darwin records retrieval/snapshot times and optional publication/update dates. Unknown source dates remain unknown. Phase 1.9F supplied-material mode does not verify live 2026 freshness.

## 32. Operational Benchmark

Phase 1.9F ran `SUPPLIED_MATERIAL_OPERATIONAL_BENCHMARK` over the cross-exchange spot arbitrage viability question. It used benchmark-local supplied-material providers and the actual `ResearchLoopController`.

## 33. Benchmark Metrics / Results

Final 1.9F benchmark:

- state: `COMPLETED`
- stop reason: `SUCCESS_COMPLETE`
- completion assessment: `COMPLETE`
- required plan items: 10 / 10 satisfied
- searches: 10
- Sources: 10
- successful snapshots: 10
- segments: 10
- Evidence candidates: 10
- accepted Evidence: 10
- Claim candidates: 10
- accepted Claims: 10
- ClaimEvidence links: 10
- validation distribution: `SUPPORTED: 10`
- provider calls: 113 / 130
- narrative findings: 13
- report published and artifact verified

## 34. Identified Defects / Fixes

Resolved:

- duplicate registered source IDs could consume duplicate fetch budget; fixed by deduplicating source IDs before fetch and adding a regression.
- supplied benchmark material initially contained action-shaped language rejected by narrative validation; fixed by rephrasing as operational observations and adding the operational benchmark regression.

## 35. Tests / Evolution

Test coverage grew from foundation checks to planner, extraction, Claim assistance, narrative synthesis, research loop, CLI, migration, benchmark, provenance, budget, stop, and resume regression coverage.

## 36. Migrations

Phase 1.9 migrations:

- `0007_research_planning`
- `0008_assisted_evidence_extraction`
- `0009_assisted_claim_construction`
- `0010_narrative_synthesis`
- `0011_research_loop`

Continuity from Phase 1.8 migrations remains intact.

## 37. Configuration

Settings now cover provider selection, model identifiers, method/prompt/schema versions, content limits, candidate limits, narrative/report limits, and research-loop system maxima.

## 38. CLI

The CLI exposes planning, candidate proposal/accept/reject, source acquisition, content fetch, explicit extraction, claim construction, validation, structured synthesis, narrative synthesis, publication, and research-loop start/show/events/resume commands.

## 39. Limitations

- Live research remains unverified without credentials.
- Query derivation is simple and transparent.
- Resume is limited to waiting gates.
- No operator UI exists.
- Token/cost accounting is limited for deterministic providers.

## 40. Technical Debt

- Source-to-plan relevance pruning can be improved.
- Runtime recovery from non-waiting interruption is limited.
- Narrative semantic fidelity still relies on deterministic structural checks plus bounded provider behavior.

## 41. Deferred Capabilities

Deferred: recommendation engine, trading/exchange execution, scheduled/background research, multi-agent architecture, graph/vector DBs, embeddings, browser automation, PDF/OCR/media, web UI, contradiction-investigation mode, and Phase 2 domain intelligence.

## 42. ADR Index / Status

No new ADR was needed in Phase 1.9F. ADR-001 through ADR-010 remain accepted and active.

## 43. Operational Instructions

Run tests with:

```bash
pytest
```

Run the Phase 1.9F benchmark with:

```bash
PYTHONPATH=src python benchmarks/phase-1.9f/run_operational_benchmark.py
```

Inspect loop executions with:

```bash
darwin research loop-show <execution-id>
darwin research loop-events <execution-id>
```

## 44. Recovery Tags / Checkpoints

Relevant tags verified:

- `phase-1.8`
- `phase-1.9a`
- `phase-1.9b`
- `phase-1.9c`
- `phase-1.9d`
- `phase-1.9e`

The recommended closure tag is `phase-1.9f` after review and commit.

## 45. Lessons Learned

The 1.9F benchmark showed that integrity checks catch useful operational issues: duplicated source fetches distort metrics, and narrative no-recommendation validation can stop report publication until material is phrased safely.

## 46. Recommendation For Phase 2

Phase 2 should begin only after Phase 1.9 is committed and tagged. Strong candidates are controlled live-provider benchmarking, improved source-plan relevance pruning, operator review UI, richer recovery, and domain-specific contradiction investigation. Recommendation, trading, and execution features should remain separate gated phases.
