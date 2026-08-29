# Evidence-to-Claim and Structured Synthesis Data Model

Phase 1.8H adds claim construction audit records and explicit conclusion-to-claim links.

## ClaimConstructionRecord

Table: `claim_construction_records`

Represents one explicit construction event for a caller-supplied Claim.

Core fields:

- `id`: UUID primary key.
- `research_run_id`: required link to `research_runs`.
- `claim_id`: required link to `claims`.
- `construction_method`: currently `MANUAL_EXPLICIT`.
- `construction_method_version`: configured method version.
- `claim_statement`: exact normalized caller-supplied claim statement.
- `evidence_count`: number of selected evidence records.
- `warning_count`, `warnings`: deterministic construction warnings.
- `metadata`: sanitized caller metadata.
- `created_at`: construction timestamp.

## ClaimConstructionEvidence

Table: `claim_construction_evidence`

Represents the evidence selected for one construction audit record.

Core fields:

- `id`: UUID primary key.
- `claim_construction_record_id`: required link to `claim_construction_records`.
- `evidence_id`: required link to `evidence`.
- `relation`: explicit claim/evidence relation.
- `created_at`: link timestamp.

## ConclusionClaim

Table: `conclusion_claims`

Represents an explicit caller-supplied dependency between a persisted conclusion and a claim.

Core fields:

- `id`: UUID primary key.
- `conclusion_id`: required link to `conclusions`.
- `claim_id`: required link to `claims`.
- `relation`: `SUPPORTS_CONCLUSION`, `CONTRADICTS_CONCLUSION`, or `CONTEXTUALIZES_CONCLUSION`.
- `metadata`: sanitized caller metadata.
- `created_at`: link timestamp.

## Boundary

This model records explicit relationships. It does not implement autonomous claim generation, semantic graph traversal, a graph database, vector search, confidence scoring, or recommendation logic.
