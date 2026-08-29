# Phase 1.8B Implementation Record

## Scope

Phase 1.8B adds the minimum persistent domain model required for Darwin to store research work with provenance and historical traceability. It defines storage foundations only.

## Files Changed

- `src/darwin/db/models.py`
- `src/darwin/db/__init__.py`
- `alembic/versions/0001_core_research_data_model.py`
- `tests/test_models.py`
- `tests/test_migrations.py`
- `README.md`
- `docs/README.md`
- `docs/data_model/core-research-data-model.md`
- `docs/decisions/ADR-005-core-research-data-model-foundation.md`
- `docs/implementation-record-phase-1.8b.md`

## Schema Created

- `research_runs`
- `sources`
- `evidence`
- `claims`
- `claim_evidence`
- `conclusions`

The migration also creates PostgreSQL enum types for run status, source type, evidence type, claim type, claim status, claim/evidence relation, and conclusion status.

## Migration Created

- Revision: `0001_core_research_data_model`
- File: `alembic/versions/0001_core_research_data_model.py`

The migration defines both upgrade and downgrade paths.

## Tests

Added deterministic tests for:

- model imports
- SQLAlchemy metadata table registration
- required fields
- enum/status behavior
- evidence-to-source provenance
- evidence-to-research-run provenance
- claim-to-research-run relationship
- claim/evidence relationship semantics
- conclusion-to-research-run relationship
- confidence nullability and range constraints
- Alembic revision loading and offline SQL compilation

## Verification Performed

- Verified working directory with `pwd`.
- Inspected `git status`, current branch, existing ADRs, database foundation, and tests before editing.
- Ran `.venv/bin/python -m pytest`; all tests passed.
- Ran `.venv/bin/darwin --help`; CLI loaded and displayed Phase 1.8A commands.
- Ran `.venv/bin/darwin status`; CLI returned `Darwin status: ok`.
- Ran `.venv/bin/alembic upgrade head --sql`; Alembic loaded the project configuration and generated PostgreSQL DDL for the Phase 1.8B migration without requiring a live database.
- Ran `.venv/bin/alembic downgrade 0001_core_research_data_model:base --sql`; Alembic generated downgrade SQL for dropping the Phase 1.8B schema.
- Ran `git diff --check`.
- Ran `git status --short`.

## Deviations

No intentional deviations from the Phase 1.8B scope.

## Limitations

- No live PostgreSQL database is provisioned.
- No source fetching, scraping, or ingestion is implemented.
- No research planning, execution, extraction, validation, synthesis, recommendation, retrieval, or orchestration runtime is implemented.
- No pgvector, vector database, graph database, or multi-agent system is implemented.
- Human validation is not implemented, though the schema keeps confidence nullable and explicit for future validation work.

## Explicit Non-Implementation Confirmation

Phase 1.8B does not implement Phase 1.8C+ runtime or research functionality. It only adds persistent domain storage foundations, tests, migration, and documentation.
