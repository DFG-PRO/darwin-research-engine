# Phase 1.8C Implementation Record

## Objective

Implement the minimum service layer required to create, update, link, and retrieve persisted research records using the Phase 1.8B data model.

## Scope

Phase 1.8C adds lifecycle and persistence behavior only. It does not add research automation, external integrations, AI generation, validation algorithms, synthesis logic, recommendations, retrieval, or UI.

## Files Changed

- `src/darwin/research/__init__.py`
- `src/darwin/research/errors.py`
- `src/darwin/research/schemas.py`
- `src/darwin/research/service.py`
- `src/darwin/db/models.py`
- `src/darwin/cli/app.py`
- `tests/test_research_service.py`
- `tests/test_cli.py`
- `README.md`
- `docs/README.md`
- `docs/data_model/core-research-data-model.md`
- `docs/runtime/research-run-lifecycle.md`
- `docs/implementation-record-phase-1.8c.md`

## Lifecycle Behavior Implemented

- Create research runs.
- Read research runs by UUID or public ID.
- Mark research runs started.
- Mark research runs completed.
- Mark research runs failed.
- Reject invalid lifecycle transitions explicitly.

## Validation Rules Implemented

- Evidence requires an existing research run and source.
- Claims require an existing research run.
- Conclusions require an existing research run.
- Claim/evidence links require an existing claim and evidence.
- Claim/evidence links must connect records from the same research run.
- Duplicate claim/evidence links raise an explicit error.
- Confidence remains explicit and nullable, and must be between 0 and 1 when provided.
- Source registration reuses deterministic duplicates by fingerprint or source type plus canonical locator.

## CLI Changes

Added `darwin research` commands:

- `darwin research create-run`
- `darwin research get-run`

The CLI is a thin interface over `ResearchService`.

## Tests

Added deterministic service tests for:

- research run creation and retrieval
- valid and invalid lifecycle transitions
- completion and failure behavior
- source registration and duplicate reuse
- evidence provenance requirements
- claim registration
- claim/evidence relationship semantics
- invalid cross-run claim/evidence relationships
- duplicate relationship protection
- conclusion registration
- traceable assembled research record retrieval
- transaction rollback behavior

## Deviations

No intentional deviations from the Phase 1.8C scope.

## Limitations

- Service tests use isolated SQLAlchemy persistence without requiring live PostgreSQL.
- No live PostgreSQL instance is provisioned.
- No background worker, workflow engine, or orchestrator runtime exists.
- No research execution or external data collection exists.

## Explicit Deferred Functionality

Deferred to later phases:

- web browsing
- external APIs
- source fetching
- AI/LLM calls
- research framing and planning
- automatic evidence extraction
- automatic claim generation
- validation methodology
- source quality scoring
- confidence scoring
- human validation workflow
- synthesis and recommendations
- memory retrieval
- embeddings, pgvector, vector DB, graph DB
- multi-agent systems
- scheduled/background research
- market/exchange adapters
- Arbitrage Engine integration
- web UI

## Verification Performed

- `pwd`
- `git status --short`
- `git branch --show-current`
- `git tag --list`
- `.venv/bin/python -m pytest`
- `.venv/bin/darwin --help`
- `.venv/bin/darwin status`
- `.venv/bin/darwin research --help`
- `.venv/bin/alembic upgrade head --sql`
- `git diff --check`

## Phase Boundary Confirmation

No Phase 1.8D+ functionality was implemented.
