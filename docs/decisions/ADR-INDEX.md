# ADR Index

| ADR | Title | Status | Phase | Rationale | Current State |
| --- | --- | --- | --- | --- | --- |
| ADR-001 | Python as primary language | Accepted | 1.8A | Python supports the initial backend, CLI, SQLAlchemy, Alembic, and tests with low complexity. | Active |
| ADR-002 | PostgreSQL as primary persistent store | Accepted | 1.8A | Darwin's durable research history needs relational integrity, JSONB, and migration support. | Active |
| ADR-003 | Modular monolith / single orchestrator for v0.1 | Accepted | 1.8A | v0.1 needs traceability and coherence before distributed execution complexity. | Active |
| ADR-004 | No separate vector DB or graph DB in v0.1 | Accepted | 1.8A | Specialized stores are deferred until proven necessary by validated retrieval needs. | Active |
| ADR-005 | Core research data model foundation | Accepted | 1.8B | ResearchRun, Source, Evidence, Claim, ClaimEvidence, and Conclusion provide the first provenance chain. | Active |
| ADR-006 | Claim validation history and source lineage | Accepted | 1.8D | Validation must be auditable, append-friendly, and guarded against false source independence. | Active |
| ADR-007 | Deterministic supplied-material orchestration | Accepted | 1.8E | The first research method should exercise the pipeline without autonomous inference. | Active |
| ADR-008 | Provider-agnostic acquisition audit | Accepted | 1.8F | External discovery needs auditable provider history without turning snippets into evidence or truth. | Active |
| ADR-009 | Source content artifact and snapshot strategy | Accepted | 1.8G | Raw/normalized content should be append-friendly and traceable without storing large blobs in every query. | Active |
| ADR-010 | Explicit claim construction and structured synthesis | Accepted | 1.8H | Claims and conclusions must remain caller-supplied while preserving evidence-grounded traceability. | Active |
