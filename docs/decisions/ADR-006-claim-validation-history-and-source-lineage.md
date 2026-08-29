# ADR-006: Claim Validation History and Source Lineage

## Status

Accepted

## Context

Phase 1.8D requires deterministic claim validation without truth judgment or confidence scoring. Darwin also needs to avoid treating repeated or derived source material as independent corroboration.

## Decision

Represent source independence through explicit source lineage fields on `sources`: `origin_source_id` and `source_lineage_type`.

Persist claim validation as append-only evaluation records in `claim_validation_evaluations`. Represent explicit human review and validation events separately in `claim_human_validations`.

## Consequences

- Distinct source rows are not automatically treated as independent sources.
- Derived and republished source relationships can be represented without automatic discovery.
- Each validation evaluation preserves counts, state, reason codes, timestamp, and method version.
- Human validation remains explicit and auditable.
- This decision does not introduce confidence scoring, semantic validation, source reputation scoring, vector search, graph storage, pgvector, or AI/LLM calls.
