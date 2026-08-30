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

### AssistedEvidenceExtractionRequest

Phase 1.9B adds assisted extraction request persistence before canonical Evidence acceptance.

Core fields:

- `id`: UUID primary key.
- `research_run_id`: required link to the research run.
- `research_plan_item_id`: required link to the plan item that caused extraction.
- `source_id`: required source link.
- `snapshot_id`: required source content snapshot link.
- `segment_ids`: JSONB list of selected segment ids.
- `research_objective`: objective supplied to the extraction boundary.
- `evidence_requirement`: plan-item evidence requirement.
- `expected_evidence_type`: optional expected canonical Evidence type.
- `extraction_instructions`: optional caller instructions.
- `freshness_start`, `freshness_end`: optional freshness context.
- `max_candidate_count`: request-level candidate bound.
- provider/model/response fields.
- method, prompt, and schema version fields.
- `status`: `COMPLETED` or `FAILED`.
- candidate, warning, and error counts.
- warnings, errors, request payload, validation result, provider metadata, usage metadata, cost metadata, and request metadata.
- `created_at`, `completed_at`: timestamps.

### EvidenceCandidateProposal

Represents a provider-proposed evidence candidate. It is not canonical Evidence.

Core fields:

- `id`: UUID primary key.
- `extraction_request_id`: required link to the assisted extraction request.
- `research_run_id`, `research_plan_item_id`, `source_id`, `snapshot_id`, `source_content_segment_id`: explicit provenance.
- `evidence_id`: nullable link populated only after explicit acceptance.
- `candidate_key`: key unique within the extraction request.
- `exact_excerpt`: provider-proposed text.
- `start_offset`, `end_offset`: segment-relative offsets.
- `proposed_evidence_type`: proposed Evidence type.
- `relevance_explanation`: provider explanation.
- `supports_research_task`: whether the provider says it supports the task.
- `temporal_applicability`: optional applicability note.
- `status`: `VALIDATED`, `REJECTED_INVALID_GROUNDING`, `REJECTED`, or `ACCEPTED`.
- `acceptance_mode`: nullable `MANUAL` or `AUTO_ACCEPTED`.
- acceptance/rejection timestamps and rejection reason.
- provider warnings, structural validation, grounding validation, and provider metadata.
- `created_at`: candidate creation timestamp.

Canonical Evidence remains stored only in `evidence`.

### AssistedClaimConstructionRequest

Phase 1.9C adds assisted claim construction request persistence before canonical Claim acceptance.

Core fields:

- `id`: UUID primary key.
- `research_run_id`: required link to the research run.
- `research_plan_item_id`: required link to the plan item that caused construction.
- `evidence_ids`: JSONB list of canonical Evidence ids submitted to the provider boundary.
- `research_objective`: objective supplied to the construction boundary.
- `construction_instruction`: caller instruction for candidate construction.
- `expected_claim_type`: optional expected canonical Claim type.
- `temporal_scope`: optional temporal scope for proposed Claims.
- `max_candidate_count`: request-level candidate bound.
- provider/model/response fields.
- construction method, prompt, and schema version fields.
- `status`: `COMPLETED` or `FAILED`.
- candidate, accepted-candidate, warning, and error counts.
- warnings, errors, request payload, validation result, provider metadata, usage metadata, cost metadata, and request metadata.
- `created_at`, `completed_at`: timestamps.

### ClaimCandidateProposal

Represents a provider-proposed Claim candidate. It is not a canonical Claim.

Core fields:

- `id`: UUID primary key.
- `construction_request_id`: required link to the assisted claim construction request.
- `research_run_id`, `research_plan_item_id`: explicit provenance.
- `claim_id`: nullable link populated only after explicit acceptance.
- `candidate_key`: key unique within the construction request.
- `proposed_claim_text`: proposed atomic Claim statement.
- `proposed_claim_type`: proposed Claim type.
- `temporal_scope`: optional temporal scope.
- `qualifiers`: JSONB list of qualifiers.
- `assumptions`: JSONB list of assumptions.
- `construction_rationale`: provider explanation.
- `status`: `VALIDATED`, `REJECTED_INVALID_PROVENANCE`, `REJECTED`, or `ACCEPTED`.
- `acceptance_mode`: nullable `MANUAL` or `AUTO_ACCEPTED`.
- acceptance/rejection timestamps and rejection reason.
- provider warnings, validation result, and provider metadata.
- `created_at`: candidate creation timestamp.

Canonical Claims remain stored only in `claims`.

### ClaimCandidateEvidence

Represents Evidence selected by a Claim candidate with Darwin relationship semantics.

Core fields:

- `id`: UUID primary key.
- `claim_candidate_id`: required link to the Claim candidate.
- `evidence_id`: required link to canonical Evidence.
- `relation`: `SUPPORTS`, `CONTRADICTS`, or `CONTEXTUALIZES` for accepted candidate construction.
- `created_at`: relationship creation timestamp.

## Provenance Model

Provenance is relational, not hidden in JSON:

- Evidence must link to a source.
- Evidence must link to a research run.
- Claims link to research runs.
- Claim/evidence semantics are stored in `claim_evidence.relation`.
- Conclusions link to research runs.
- Research plan proposals may link to one approved research run.
- Research plan proposals have many proposed plan item rows.
- Assisted extraction requests link to one research run, plan item, source, and snapshot.
- Evidence candidate proposals link to one assisted extraction request and one source content segment.
- Accepted evidence candidate proposals may link to one canonical Evidence row.
- Assisted claim construction requests link to one research run, plan item, and a bounded set of canonical Evidence ids.
- Claim candidate proposals link to one assisted claim construction request.
- Claim candidate Evidence links preserve proposed Evidence-role semantics before canonical Claim acceptance.
- Accepted Claim candidate proposals may link to one canonical Claim row.

This allows future validation, contradiction tracking, and historical retrieval work to build on explicit relationships.

Phase 1.8C retrieval returns sources used through evidence, evidence, claims, claim/evidence relationships, and conclusions in one traceable read model.

Phase 1.9A planning proposal provenance is intentionally separate from Evidence, Claims, and Conclusions. A proposal may suggest what evidence to seek, but it does not create or validate evidence.

Phase 1.9B evidence candidate provenance is also separate from canonical Evidence until explicit acceptance. A candidate must be exactly grounded in stored segment text before it can be accepted.

Phase 1.9C Claim candidate provenance is separate from canonical Claims until explicit acceptance. A candidate must be grounded in canonical Evidence before it can be accepted into a Claim and ClaimEvidence links.

## Lifecycle and Status Concepts

Current enum sets are intentionally small:

- Research runs: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`.
- Claims: `PROPOSED`, `UNDER_REVIEW`, `RESOLVED`, `REJECTED`.
- Conclusions: `DRAFT`, `FINAL`, `SUPERSEDED`.
- Research plan proposals: `PROPOSED`, `APPROVED`, `REJECTED`, `FAILED`.
- Research plan approval modes: `MANUAL`, `AUTO_APPROVED`.
- Assisted extraction requests: `COMPLETED`, `FAILED`.
- Evidence candidates: `VALIDATED`, `REJECTED_INVALID_GROUNDING`, `REJECTED`, `ACCEPTED`.
- Evidence candidate acceptance modes: `MANUAL`, `AUTO_ACCEPTED`.
- Assisted claim construction requests: `COMPLETED`, `FAILED`.
- Claim candidates: `VALIDATED`, `REJECTED_INVALID_PROVENANCE`, `REJECTED`, `ACCEPTED`.
- Claim candidate acceptance modes: `MANUAL`, `AUTO_ACCEPTED`.

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
- `assisted_evidence_extraction_requests.request_payload`
- `assisted_evidence_extraction_requests.validation_result`
- `evidence_candidate_proposals.structural_validation`
- `evidence_candidate_proposals.grounding_validation`
- `assisted_claim_construction_requests.evidence_ids`
- `assisted_claim_construction_requests.request_payload`
- `assisted_claim_construction_requests.validation_result`
- `claim_candidate_proposals.qualifiers`
- `claim_candidate_proposals.assumptions`
- `claim_candidate_proposals.validation_result`
- `claim_candidate_proposals.provider_metadata`
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
