# Phase 1.8 Master Record

## Executive Summary

Phase 1.8 established Darwin's Research MVP foundation: a Python modular monolith with PostgreSQL-oriented persistence, auditable research lifecycle records, source/evidence/claim/conclusion traceability, deterministic validation, controlled acquisition, content snapshots, explicit evidence extraction, explicit claim construction, and structured synthesis.

## Phase Objective

Build the minimum durable foundation for traceable research without implementing autonomous research, multi-agent execution, LLM claim generation, semantic contradiction detection, recommendations, vector search, graph storage, or trading execution.

## Initial State Before 1.8

The repository did not yet have the complete production-oriented Python foundation, data model, migrations, research lifecycle services, validation chain, acquisition layer, content snapshotting, claim construction, or structured synthesis required for Darwin v0.1.

## Final State After 1.8

Darwin can run a deterministic supplied-material research pipeline with persisted ResearchRuns, Sources, Snapshots, Segments, Evidence, Claims, validation history, synthesis records, Conclusions, and conclusion-to-claim links.

## Evolution By Subphase

- 1.8A: repository foundation, settings, logging, SQLAlchemy, Alembic, CLI, tests, docs.
- 1.8B: core research data model.
- 1.8C: ResearchRun lifecycle and persistence services.
- 1.8D: claim validation history, reason codes, human validation events, and source lineage.
- 1.8E: deterministic supplied-material research orchestrator.
- 1.8F: provider-agnostic external acquisition audit.
- 1.8G: source content fetching, artifacts, snapshots, segments, and explicit Evidence extraction.
- 1.8H: explicit evidence-to-claim construction and structured synthesis.
- 1.8I: benchmark, audit, documentation consolidation, and closure assessment.

## Final Architecture

Darwin v0.1 is a modular monolith with a single deterministic orchestrator. Service modules coordinate persistence, acquisition, content processing, construction, validation, and synthesis while sharing one SQLAlchemy data model.

## Repository/Module Map

- `src/darwin/config`: Pydantic Settings configuration.
- `src/darwin/db`: SQLAlchemy base, models, engine, sessions.
- `src/darwin/research`: core persistence service.
- `src/darwin/validation`: deterministic claim validation.
- `src/darwin/orchestration`: supplied-material research orchestration.
- `src/darwin/acquisition`: provider-agnostic source discovery.
- `src/darwin/content`: source fetch, artifact, snapshot, segment, evidence extraction.
- `src/darwin/construction`: explicit evidence-to-claim construction.
- `src/darwin/synthesis`: structured synthesis and conclusion traceability.
- `src/darwin/cli`: Typer CLI.
- `alembic/versions`: migrations `0001` through `0006`.
- `benchmarks/phase-1.8i`: Research MVP benchmark artifacts.

## Configuration Model

Configuration is environment-driven through Pydantic Settings with `DARWIN_` variables. Key settings cover runtime environment, logging, Darwin version, research method version, artifact root, database URL, acquisition provider, source fetch constraints, content/evidence method versions, claim construction method version, synthesis method version, and claim statement bounds.

## Database/Data Model

Core tables include `research_runs`, `sources`, `evidence`, `claims`, `claim_evidence`, `conclusions`, validation history, framing/plan/synthesis records, acquisition requests/candidates, source content snapshots/segments, evidence extraction records, claim construction records, construction evidence selections, and conclusion claim links.

## Migration History

- `0001_core_research_data_model`
- `0002_claim_validation_foundation`
- `0003_research_method_orchestration`
- `0004_external_research_acquisition`
- `0005_source_content_acquisition`
- `0006_claim_construction_synthesis`

Offline upgrade to head and current-head downgrade compile successfully.

## ResearchRun Lifecycle

ResearchRuns begin as `PENDING`, move to `IN_PROGRESS`, and are marked `COMPLETED` only when completion assessment is `COMPLETE`. Incomplete, contested, and human-review-pending outcomes remain explicit.

## Research Method v0.1

The method follows:

```text
Research Question -> Framing -> Plan -> Sources -> Snapshot -> Segment -> Evidence
-> Claim -> Validation -> Structured Synthesis -> Conclusion -> Completion Assessment
```

## Acquisition Layer

External acquisition records provider, query, constraints, candidates, registration outcomes, warnings, and errors. Provider snippets are not Evidence or Claims.

## Content/Snapshot Layer

Supported HTML/text content can be fetched explicitly. Raw and normalized artifacts are stored under `DARWIN_ARTIFACT_ROOT`; snapshots and segments remain append-friendly.

## Evidence Methodology

Evidence extraction is explicit from a segment or exact span. Evidence preserves Source and, when content-derived, Snapshot/Segment provenance.

## Claim Construction

Claims require caller-supplied text and selected evidence. `MANUAL_EXPLICIT` is the only construction method in v0.1.

## Claim Validation

Validation is structural. States include insufficient evidence, supported, corroborated, contested, contradicted, human review pending, and human validated. It does not decide truth.

## Source Independence / Lineage

Derived and republished sources point to origin sources. Validation counts independent source origins to prevent false corroboration.

## Structured Synthesis

Structured synthesis is deterministic and append-only. It preserves claim provenance, validation state, conclusion dependencies, evidence gaps, unresolved contradictions, and warnings.

## Conclusion Traceability

Conclusions can be explicitly linked to Claims with support, contradiction, or contextualization relationships.

## Completion Assessment

The completion gate distinguishes complete, incomplete, needs evidence, unresolved contradiction, and human review required.

## Human Validation Policy

Human validation is exceptional. Human review and human validation are explicit events and do not become independent source corroboration.

## Artifact Storage

Artifacts are path-checked and stored under configured artifact root. Large raw pages are not committed.

## Security Boundaries

Current protections include secret-shaped metadata redaction, unsupported scheme handling, response size limits, artifact path traversal checks, no committed secrets, no automatic execution/trading, and no browser automation.

## Transaction Model

Services accept explicit SQLAlchemy sessions. Callers own transaction boundaries. CLI uses `session_scope`; tests verify rollback behavior for failure paths.

## CLI Capabilities

CLI commands cover status, database status, research run creation/inspection, validation, manual orchestration, acquisition, source content fetch/list/extract, claim construction, claim inspection, and synthesis.

## Tests And Evolution

The final full suite has 98 tests. Coverage areas include configuration, CLI, migrations, models, lifecycle, validation, acquisition, source content, evidence extraction, claim construction, synthesis, orchestration, and Phase 1.8I benchmark regressions.

## Benchmark Methodology

Phase 1.8I used `SUPPLIED_MATERIAL_BENCHMARK` mode because Brave credentials were absent. The benchmark used curated supplied material to exercise the full downstream pipeline without fabricating live research.

## Benchmark Results

The benchmark produced 10/10 plan coverage, 8 snapshot-derived Evidence records, 11 Claims, 8 supported Claims, 2 corroborated Claims, 1 contested Claim, no evidence gaps, and completion assessment `UNRESOLVED_CONTRADICTION`. False corroboration from a mirrored fee source was prevented.

## Known Limitations

Live acquisition was not verified. The benchmark material is not current live exchange documentation. Darwin still requires manual evidence selection and claim construction.

## Technical Debt

Documentation is now consolidated, but future phases may benefit from a formal benchmark runner interface and a richer report export format.

## Deferred Capabilities

Deferred: autonomous research, LLM extraction, semantic contradiction detection, confidence scoring, recommendations, retrieval memory, vector DB, graph DB, pgvector, browser automation, PDF/OCR/media extraction, scheduled research, automatic trading, and web UI.

## ADR Index

See `docs/decisions/ADR-INDEX.md`.

## Operational Instructions

Install with `python -m pip install -e ".[dev]"`, configure `.env` from `.env.example`, run `pytest`, inspect CLI with `darwin --help`, and manage migrations with Alembic.

## Recovery/Checkpoint/Tag Strategy

No commit, push, or tag was performed during Phase 1.8I. Recommended final tag after external audit: `phase-1.8`.

## Lessons Learned

Darwin's strongest MVP property is provenance discipline. Its main current limitation is that source acquisition and evidence selection remain manual or supplied-material driven without live credentialed verification in this benchmark.

## Recommended Phase 1.9 Direction

Phase 1.9 should focus on live research acquisition verification and controlled evidence intake improvements while preserving the current provenance and completion-gate guarantees.
