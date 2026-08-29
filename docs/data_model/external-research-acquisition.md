# External Research Acquisition Data Model

Phase 1.8F adds persistence for external source discovery audit history.

## ResearchAcquisitionRequest

Table: `research_acquisition_requests`

Represents one explicit search/discovery request attached to a research run.

Core fields:

- `id`: UUID primary key.
- `research_run_id`: required link to `research_runs`.
- `provider_id`: provider adapter identifier.
- `provider_request_id`: optional provider-side request/reference ID.
- `query`: original search query.
- `category`: optional generic request category.
- `requested_source_types`: requested source type values.
- `freshness_start`, `freshness_end`: optional date constraints.
- `domain_constraints`: optional domain constraints supplied by the caller.
- `result_limit`: requested candidate limit.
- `status`: `SUCCESS`, `PARTIAL`, or `FAILED`.
- `executed_at`, `completed_at`: execution timestamps.
- `candidate_count`, `registered_source_count`: result counters.
- `warning_count`, `error_count`: provider/result issue counters.
- `retry_attempts`, `request_count`: retry and request accounting.
- `usage_units`, `estimated_cost`, `actual_cost`: nullable cost/usage values.
- `warnings`, `errors`: explicit provider warnings and errors.
- `metadata`: sanitized request metadata.
- `provider_metadata`: sanitized provider metadata.
- `rate_limit_metadata`: rate-limit information when supplied.

## SourceCandidate

Table: `source_candidates`

Represents one provider-returned candidate before any evidence extraction or claim work.

Core fields:

- `id`: UUID primary key.
- `acquisition_request_id`: required link to `research_acquisition_requests`.
- `provider_candidate_id`: optional provider-side candidate ID.
- `canonical_locator`: provider-returned locator.
- `normalized_locator`: deterministic normalized locator.
- `deduplication_key`: conservative deterministic duplicate key.
- `title`, `publisher`, `normalized_domain`: descriptive source metadata when known.
- `publication_date`: provider-supplied publication date when known.
- `retrieved_at`: candidate discovery timestamp.
- `snippet`: provider-returned snippet for audit only.
- `provider_rank`: provider result rank when supplied.
- `source_type`: source type when deterministically known.
- `registration_status`: registration outcome.
- `duplicate_of_candidate_id`: candidate duplicate reference when applicable.
- `registered_source_id`: linked `sources.id` when the candidate is registered.
- `provider_metadata`: sanitized candidate-level provider metadata.

## Registration Status

`source_candidate_registration_status` values:

- `REGISTERED_NEW_SOURCE`
- `REGISTERED_EXISTING_SOURCE`
- `DUPLICATE_CANDIDATE`
- `NOT_REGISTERED`
- `REGISTRATION_FAILED`

## Relationship Boundary

The acquisition model preserves:

```text
ResearchRun -> ResearchAcquisitionRequest -> SourceCandidate -> Source
```

It does not create:

- `Evidence`
- `Claim`
- `ClaimEvidence`
- `Conclusion`

Provider snippets remain candidate audit material only.
