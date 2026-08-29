# Core Research Data Model

Phase 1.8B adds Darwin's minimum persistent research data model. It defines storage foundations only and does not implement research execution, extraction, validation, synthesis, recommendations, retrieval, or orchestration runtime.

## Entities

### ResearchRun

Represents one bounded research investigation.

Core fields:

- `id`: UUID primary key.
- `public_id`: stable public identifier that avoids exposing sequential database IDs.
- `title`: research question or investigation title.
- `status`: explicit lifecycle state.
- `created_at`, `updated_at`, `completed_at`: timezone-aware timestamps.
- `research_method_version`: method contract version used for the run.
- `darwin_version`: Darwin version used for the run.
- `context`: JSONB payload for optional contextual metadata.

### Source

Represents a source used during research.

Core fields:

- `id`: UUID primary key.
- `source_type`: explicit source category.
- `canonical_locator`: canonical URL, path, or external identifier.
- `title`, `publisher`, `publication_date`: optional descriptive metadata.
- `origin_source_id`: optional explicit link to the source this source derives from or republishes.
- `source_lineage_type`: optional lineage type such as `DERIVED_FROM` or `REPUBLISHED_FROM`.
- `retrieved_at`: timestamp for when the source was retrieved or observed.
- `content_fingerprint`: optional hash/fingerprint for content identity.
- `metadata`: JSONB payload for additional source metadata.
- `created_at`: source record creation timestamp.

### Evidence

Represents an evidence unit extracted from or derived from a source.

Core fields:

- `id`: UUID primary key.
- `research_run_id`: required link to the research run.
- `source_id`: required link to the source.
- `evidence_type`: explicit evidence category.
- `statement`: normalized evidence content.
- `source_locator`: optional locator inside the source.
- `captured_at`: timestamp for evidence capture.
- `metadata`: JSONB payload for additional evidence metadata.

Evidence always retains source provenance through `source_id`.

### Claim

Represents an explicit proposition being evaluated by Darwin.

Core fields:

- `id`: UUID primary key.
- `research_run_id`: required link to the research run.
- `statement`: claim text.
- `claim_type`: minimal claim category.
- `status`: explicit claim lifecycle state.
- `confidence`: nullable value constrained to 0 through 1 when present.
- `created_at`, `updated_at`: timezone-aware timestamps.

Confidence is nullable because Phase 1.8B does not implement confidence calculation.

### ClaimEvidence

Represents a semantic relationship between a claim and an evidence unit.

Core fields:

- `id`: UUID primary key.
- `claim_id`: required link to the claim.
- `evidence_id`: required link to the evidence.
- `relation`: explicit relationship semantic.
- `created_at`: relationship creation timestamp.

Supported relation values are `SUPPORTS`, `CONTRADICTS`, `CONTEXTUALIZES`, and `RELATED`.

### Conclusion

Represents a research-level synthesis or result.

Core fields:

- `id`: UUID primary key.
- `research_run_id`: required link to the research run.
- `statement`: conclusion text.
- `confidence`: nullable value constrained to 0 through 1 when present.
- `status`: explicit conclusion lifecycle state.
- `created_at`, `updated_at`: timezone-aware timestamps.

## Relationships

- `ResearchRun` has many `Evidence` records.
- `ResearchRun` has many `Claim` records.
- `ResearchRun` has many `Conclusion` records.
- `Source` has many `Evidence` records.
- `Evidence` belongs to one `Source`.
- `Evidence` belongs to one `ResearchRun`.
- `Claim` belongs to one `ResearchRun`.
- `ClaimEvidence` links one `Claim` to one `Evidence` with an explicit relationship semantic.
- `Conclusion` belongs to one `ResearchRun`.

Foreign keys use restrictive delete behavior to avoid accidental destructive removal of historical research state.

Phase 1.8C adds service-layer validation requiring `ClaimEvidence` records to link claims and evidence from the same research run.

Phase 1.8D adds source lineage so distinct source records are not automatically counted as independent corroboration.

### ClaimValidationEvaluation

Represents one auditable deterministic structural validation evaluation for a claim.

Core fields:

- `id`: UUID primary key.
- `claim_id`: required link to the claim.
- `validation_state`: explicit structural validation state.
- evidence/source counts used by the evaluation.
- `independent_corroboration_exists`: whether independent support exists.
- `contradiction_exists`: whether contradiction is present.
- `human_review_requested`: whether explicit human review is currently represented.
- `human_validation_present`: whether explicit human validation is currently represented.
- `reason_codes`: JSONB array of explicit reason-code strings.
- `evaluated_at`: evaluation timestamp.
- `validation_method_version`: method version used.

Evaluations are history-friendly records; new evaluations are appended rather than overwriting previous rows.

### ClaimHumanValidation

Represents an explicit human review or validation event.

Core fields:

- `id`: UUID primary key.
- `claim_id`: required link to the claim.
- `validation_type`: `REVIEW_REQUESTED` or `VALIDATED`.
- `created_at`: event timestamp.
- `validator_label`: optional non-sensitive label.
- `note`: optional note.

Human validation is never inferred.

## Provenance Model

Provenance is relational, not hidden in JSON:

- Evidence must link to a source.
- Evidence must link to a research run.
- Claims link to research runs.
- Claim/evidence semantics are stored in `claim_evidence.relation`.
- Conclusions link to research runs.

This allows future validation, contradiction tracking, and historical retrieval work to build on explicit relationships.

Phase 1.8C retrieval returns sources used through evidence, evidence, claims, claim/evidence relationships, and conclusions in one traceable read model.

## Lifecycle and Status Concepts

Current enum sets are intentionally small:

- Research runs: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`.
- Claims: `PROPOSED`, `UNDER_REVIEW`, `RESOLVED`, `REJECTED`.
- Conclusions: `DRAFT`, `FINAL`, `SUPERSEDED`.

These states provide foundation-level lifecycle clarity without implementing research execution behavior.

## Identifier Strategy

All persistent domain entities use UUID-compatible primary keys. `ResearchRun` also has a `public_id` for external-facing references, avoiding reliance on sequential database identifiers as long-term public identity.

## Timestamp Strategy

Timestamps use timezone-aware SQLAlchemy `DateTime(timezone=True)` fields. Application-side defaults use UTC timestamps, while the migration also provides database `now()` defaults for creation/capture fields where appropriate.

## JSONB Usage Rules

JSONB is used only for flexible metadata and context payloads:

- `research_runs.context`
- `sources.metadata`
- `evidence.metadata`

Core relationships, lifecycle fields, identifiers, provenance links, and confidence fields are first-class columns and must not be hidden inside JSONB.

## Service-Layer Constraints

Phase 1.8C enforces these persistence rules above the database schema:

- Research run lifecycle transitions are explicit and limited.
- Evidence requires existing source and research run records.
- Claims and conclusions require existing research run records.
- Claim/evidence links cannot cross research run boundaries.
- Duplicate claim/evidence links fail explicitly.
- Source registration reuses deterministic duplicates by fingerprint or canonical identity.
- Claim validation appends auditable evaluation records.
- Human review and validation require explicit persisted events.

## Current Limitations

- No live database is provisioned.
- No research execution pipeline exists.
- No scraping, fetching, or source ingestion exists.
- No confidence scoring is implemented.
- No human validation workflow is implemented.
- No recommendation logic is implemented.
- No memory retrieval, embeddings, pgvector, vector database, or graph database exists.

## Intentionally Deferred

- Web research and provider adapters.
- Research planner and orchestrator runtime.
- Evidence extraction and claim generation.
- Claim validation and confidence scoring.
- Synthesis and recommendation engines.
- Historical memory retrieval.
- Human validation workflows.
- Benchmarks and outcome tracking.
