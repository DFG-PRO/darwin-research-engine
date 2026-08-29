# ADR-010: Explicit Claim Construction and Structured Synthesis

## Status

Accepted for Phase 1.8H.

## Context

Darwin needs to preserve the path from source material to evidence, claims, validation state, synthesis records, and conclusions. Phase 1.8H must not infer claims or conclusions, but it must make explicit evidence-to-claim construction auditable.

## Decision

Darwin v0.1 will construct claims only from caller-supplied claim statements and explicit evidence selections. The initial method is `MANUAL_EXPLICIT`.

Structured synthesis will be deterministic and evidence-grounded. It will preserve validation state, evidence provenance, explicit conclusion-to-claim dependencies, warnings, and append-only synthesis history.

## Consequences

- Evidence selections are auditable through `claim_construction_records` and `claim_construction_evidence`.
- Conclusion dependencies are auditable through `conclusion_claims`.
- Human validation remains distinct from independent source support.
- No autonomous claim generation, semantic conclusion generation, recommendation logic, vector database, graph database, or multi-agent architecture is introduced.
- `pgvector` remains outside Phase 1.8H.
