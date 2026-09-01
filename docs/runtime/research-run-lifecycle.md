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
- List bounded research run summaries with optional status filtering.
- Validate a claim's structural evidentiary state through the validation service.

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

## Export Behavior

`export_research_record` returns a JSON-ready envelope for one research run. The
envelope includes a schema version, export timestamp, the assembled research
record, and summary counts for sources, evidence, claims, claim/evidence links,
and conclusions. The export path reuses `get_research_record` and does not add a
database mutation, schema migration, or dependency.

CLI usage:

```shell
darwin research export-run rrn_example
darwin research export-run rrn_example --output export.json
```

## Listing Behavior

`list_research_runs` returns read-only `ResearchRun` summaries ordered by latest update first.
It accepts an optional status filter and a bounded result limit, and includes aggregate
counts for distinct sources, evidence, claims, and conclusions. The query uses existing
research lifecycle tables only; it does not require a schema migration or new dependency.

CLI usage:

```shell
darwin research list-runs --status completed --limit 25
```

## Error Behavior

The research service defines a small explicit error model:

- `ResearchRunNotFound`
- `InvalidResearchRunTransition`
- `InvalidResearchRelationship`
- `DuplicateResearchRelationship`

These errors are intentionally narrow and structural.

## Claim Validation Behavior

Phase 1.8D adds `ClaimValidationService` as a separate service from research persistence CRUD. It loads an existing claim, evidence links, source records, and human validation events, then persists an auditable validation evaluation.

The validation service:

- classifies already-stored claim/evidence relationships
- counts supporting, contradicting, and contextual evidence
- counts distinct sources and independent source origins
- respects explicit source lineage
- records reason codes and method version
- appends validation history

It does not fetch sources, classify evidence, determine truth, or calculate numeric confidence.

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
