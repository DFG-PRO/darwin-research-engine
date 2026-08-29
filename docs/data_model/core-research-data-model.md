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

### ResearchFraming

Represents one auditable framing record for a research run.

Core fields:

- `id`: UUID primary key.
- `research_run_id`: required link to the research run.
- `original_question`: caller's original research question.
- `normalized_question`: deterministic normalized question.
- `objective`: research objective.
- `scope`: stated research scope.
- `exclusions`: JSONB list of out-of-scope items.
- `key_decision_criteria`: JSONB list of decision criteria.
- `assumptions`: JSONB list of assumptions.
- `required_evidence_categories`: JSONB list of expected evidence categories.
- `completion_criteria`: JSONB list of completion criteria.
- `metadata`: JSONB payload for framing metadata.
- `created_at`: framing record creation timestamp.

### ResearchPlanItem

Represents one auditable plan requirement for a research run.

Core fields:

- `id`: UUID primary key.
- `research_run_id`: required link to the research run.
- `item_key`: caller-facing key unique within the research run.
- `requirement`: evidence requirement or task.
- `category`: generic evidence category.
- `priority`: `LOW`, `MEDIUM`, or `HIGH`.
- `is_required`: whether completion requires this plan item.
- `status`: `PENDING`, `SATISFIED`, or `WAIVED`.
- `expected_source_type`: optional expected source type.
- `notes`: optional notes.
- `created_at`, `updated_at`: timestamps.

### ResearchSynthesisRecord

Represents one auditable deterministic synthesis record for a research run.

Core fields:

- `id`: UUID primary key.
- `research_run_id`: required link to the research run.
- `research_method_version`: method version used.
- `completion_assessment`: deterministic completion assessment.
- source, evidence, claim, and conclusion counts.
- `evidence_gaps`: JSONB list of required plan item keys still missing evidence.
- `unresolved_contradictions`: JSONB list of contested claim keys.
- `warnings`: JSONB list of structural warnings.
- `payload`: JSONB structured output snapshot.
- `created_at`: synthesis timestamp.

### ResearchPlanProposal

Phase 1.9A adds append-only proposal persistence before a research run is approved.

Core fields:

- `id`: UUID primary key.
- `research_run_id`: nullable link to the approved `ResearchRun`, populated only after approval.
- `original_question`: caller's original planning question.
- `normalized_question`: provider-normalized question.
- `objective`: proposed research objective.
- `scope`: proposed research scope.
- `exclusions`: JSONB list of proposed exclusions.
- `assumptions`: JSONB list of proposed assumptions.
- `research_categories`: JSONB list of proposed research categories.
- `expected_evidence_types`: JSONB list of evidence types expected during later execution.
- `suggested_source_types`: JSONB list of source types suggested for later acquisition.
- `status`: `PROPOSED`, `APPROVED`, `REJECTED`, or `FAILED`.
- `approval_mode`: nullable `MANUAL` or `AUTO_APPROVED`.
- `approved_at`: approval timestamp when approved.
- `provider_id`, `provider_model`, `provider_response_id`: provider provenance.
- `planner_method_version`, `prompt_version`, `schema_version`: planning behavior versions.
- `warnings`, `errors`, `validation_result`: planning diagnostics.
- `planning_request`: JSONB snapshot of the caller request.
- `proposal_payload`: JSONB snapshot of the validated structured proposal.
- `provider_metadata`, `usage_metadata`, `cost_metadata`: non-secret provider metadata.
- `metadata`: additional planning provenance.
- `created_at`: proposal creation timestamp.

### ResearchPlanProposalItem

Represents one proposed task before approval.

Core fields:

- `id`: UUID primary key.
- `proposal_id`: required link to `ResearchPlanProposal`.
- `item_key`: proposal-facing key unique within a proposal.
- `requirement`: proposed task requirement.
- `category`: proposed research category.
- `priority`: `LOW`, `MEDIUM`, or `HIGH`.
- `is_required`: whether the task is required in the proposal.
- `status`: always `PENDING` at proposal time.
- `expected_source_type`: optional primary source type.
- `expected_evidence_types`: JSONB list of expected evidence types.
- `suggested_source_types`: JSONB list of suggested source types.
- `completion_criteria`: JSONB list of explicit task completion criteria.
- `notes`: optional notes.
- `item_order`: stable display order from the provider proposal.
- `created_at`: proposal item creation timestamp.

Approval copies proposal content into the existing `ResearchFraming` and `ResearchPlanItem` models. Planning proposal records do not replace Phase 1.8 research plans.

## Provenance Model

Provenance is relational, not hidden in JSON:

- Evidence must link to a source.
- Evidence must link to a research run.
- Claims link to research runs.
- Claim/evidence semantics are stored in `claim_evidence.relation`.
- Conclusions link to research runs.
- Research plan proposals may link to one approved research run.
- Research plan proposals have many proposed plan item rows.

This allows future validation, contradiction tracking, and historical retrieval work to build on explicit relationships.

Phase 1.8C retrieval returns sources used through evidence, evidence, claims, claim/evidence relationships, and conclusions in one traceable read model.

Phase 1.9A planning proposal provenance is intentionally separate from Evidence, Claims, and Conclusions. A proposal may suggest what evidence to seek, but it does not create or validate evidence.

## Lifecycle and Status Concepts

Current enum sets are intentionally small:

- Research runs: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`.
- Claims: `PROPOSED`, `UNDER_REVIEW`, `RESOLVED`, `REJECTED`.
- Conclusions: `DRAFT`, `FINAL`, `SUPERSEDED`.
- Research plan proposals: `PROPOSED`, `APPROVED`, `REJECTED`, `FAILED`.
- Research plan approval modes: `MANUAL`, `AUTO_APPROVED`.

These states provide foundation-level lifecycle clarity without implementing research execution behavior.

## Identifier Strategy

All persistent domain entities use UUID-compatible primary keys. `ResearchRun` also has a `public_id` for external-facing references, avoiding reliance on sequential database identifiers as long-term public identity.

## Timestamp Strategy

Timestamps use timezone-aware SQLAlchemy `DateTime(timezone=True)` fields. Application-side defaults use UTC timestamps, while the migration also provides database `now()` defaults for creation/capture fields where appropriate.

## JSONB Usage Rules

JSONB is used only for flexible metadata and context payloads:

- `research_runs.context`
- `research_plan_proposals.planning_request`
- `research_plan_proposals.proposal_payload`
- `research_plan_proposals.validation_result`
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
- Research orchestration persists framing, plan items, and synthesis records.
- Required plan items are satisfied only by explicit supplied evidence references.

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
