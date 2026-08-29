# Research Run Lifecycle and Persistence Services

Phase 1.8C adds the minimum application service layer for creating, updating, linking, and retrieving persisted research records. It does not implement research automation, source fetching, extraction, validation, synthesis, recommendations, retrieval, or orchestration runtime.

## Service Layer Responsibilities

The service layer lives in `darwin.research` and wraps deterministic persistence rules for the Phase 1.8B data model.

Implemented responsibilities:

- Create and read research runs.
- Update research run lifecycle status.
- Register sources without fetching content.
- Register evidence linked to both a research run and a source.
- Register claims linked to a research run.
- Link claims to evidence with explicit relationship semantics.
- Register conclusions linked to a research run.
- Retrieve an assembled research record with traceable components.

The CLI calls the service layer and does not duplicate lifecycle or relationship rules.

## Transaction Boundaries

`ResearchService` accepts an explicit SQLAlchemy session. The caller owns the transaction boundary.

Service methods:

- Add or update ORM records.
- Validate structural persistence rules.
- Flush changes so database constraints surface before commit.
- Do not commit partial work.
- Do not use hidden global mutable sessions.

CLI commands use the existing `session_scope` helper, which commits on success and rolls back on failure.

## Persistence Flow

Typical flow:

1. Create a `ResearchRun`.
2. Mark the run started when lifecycle work begins.
3. Register one or more `Source` records.
4. Register `Evidence` records linked to both `ResearchRun` and `Source`.
5. Register `Claim` records linked to the same `ResearchRun`.
6. Link claims to evidence through `ClaimEvidence`.
7. Register `Conclusion` records linked to the `ResearchRun`.
8. Retrieve the assembled research record for traceability.

## Allowed ResearchRun Transitions

Allowed transitions:

- `PENDING -> IN_PROGRESS`
- `PENDING -> FAILED`
- `IN_PROGRESS -> COMPLETED`
- `IN_PROGRESS -> FAILED`

Terminal states:

- `COMPLETED`
- `FAILED`

Transitions out of terminal states fail explicitly. `COMPLETED` and `FAILED` set `completed_at`.

## Validation Rules

Implemented structural rules:

- Missing research runs fail explicitly.
- Evidence requires an existing research run and source.
- Claims require an existing research run.
- Conclusions require an existing research run.
- Claim/evidence links require existing claim and evidence records.
- Claim/evidence links must stay within the same research run.
- Duplicate claim/evidence links fail explicitly.
- Confidence remains nullable but must be between 0 and 1 when provided.
- Duplicate source registration reuses an existing source when content fingerprint or canonical identity matches deterministically.

## Retrieval Behavior

`get_research_record` returns a Pydantic read model containing:

- research run
- sources used through evidence
- evidence
- claims
- claim/evidence relationships
- conclusions

Traceability is preserved through explicit IDs and relationship records.

## Error Behavior

The research service defines a small explicit error model:

- `ResearchRunNotFound`
- `InvalidResearchRunTransition`
- `InvalidResearchRelationship`
- `DuplicateResearchRelationship`

These errors are intentionally narrow and structural.

## Current Limitations

- No workflow engine.
- No source fetching or scraping.
- No AI or LLM calls.
- No automatic evidence extraction.
- No claim generation.
- No validation methodology.
- No confidence scoring.
- No human validation workflow.
- No synthesis or recommendation engine.
- No memory retrieval, embeddings, pgvector, vector database, graph database, or multi-agent system.
