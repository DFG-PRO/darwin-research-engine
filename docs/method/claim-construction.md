# Claim Construction Method

Phase 1.8H adds explicit evidence-to-claim construction.

## Contract

`ClaimConstructionRequest` requires:

- `research_run_id`
- caller-supplied `statement` or `claim_statement`
- `claim_type`
- selected evidence IDs
- explicit evidence relationship values: `SUPPORTS`, `CONTRADICTS`, `CONTEXTUALIZES`, or existing `RELATED`
- construction method, currently `MANUAL_EXPLICIT`
- optional sanitized metadata

The caller supplies the claim statement. Darwin does not infer, summarize, rewrite, or generate claims from evidence.

## Persistence

Claim construction uses `ResearchService` to create the Claim and claim/evidence links. It then persists:

- `claim_construction_records`
- `claim_construction_evidence`

The construction audit is append-friendly. It records method, method version, claim statement, evidence count, warnings, metadata, and selected evidence relationships.

## Validation

By default, claim construction invokes `ClaimValidationService` after persistence. The validation remains structural and deterministic. It does not decide truth, score confidence, or detect semantic contradictions.

## Eligibility

Evidence must exist, belong to the same ResearchRun, and retain Source provenance. Content-derived evidence that references source content must include valid Snapshot and Segment provenance.

## Boundary

Not implemented in Phase 1.8H:

- autonomous claim generation
- LLM extraction
- semantic contradiction detection
- confidence scoring
- recommendations
- multi-agent review
