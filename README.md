# Darwin Research & Intelligence Engine

Darwin v0.1 is the initial foundation for a research and intelligence engine intended to preserve traceable evidence, validated knowledge, historical context, confidence, outcomes, errors, contradictions, assumptions, and decisions over time.

Current status: **Phase 1.8C research run lifecycle and persistence services**. This repository provides the technical base, first persistent storage schema, and minimal service layer for creating, updating, linking, and retrieving persisted research records. It does not implement research execution, evidence extraction, claim validation, confidence scoring, recommendation systems, memory retrieval, or domain intelligence features.

## What Exists

- Python 3.12+ project using a `src/` layout.
- Centralized environment-driven configuration.
- Consistent application logging setup.
- PostgreSQL-oriented SQLAlchemy 2.x engine, session, and declarative metadata foundation.
- Alembic migration environment wired to Darwin settings and SQLAlchemy metadata.
- Core SQLAlchemy research data model and first Alembic schema migration.
- Minimal research persistence service layer for lifecycle and traceability operations.
- Minimal Typer CLI.
- Deterministic pytest coverage for imports, configuration, CLI, and database foundation setup.
- Initial documentation directories and ADRs for decisions made in Phase 1.8A.

## Local Setup

Create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install the package with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

## Environment Configuration

Configuration is read from environment variables prefixed with `DARWIN_`. For local development, copy `.env.example` to `.env` and adjust values as needed:

```bash
cp .env.example .env
```

Supported settings:

- `DARWIN_ENV`: `local`, `test`, `staging`, or `production`. Defaults to `local`.
- `DARWIN_LOG_LEVEL`: Python logging level. Defaults to `INFO`.
- `DARWIN_VERSION`: Darwin application version. Defaults to `0.1.0`.
- `DARWIN_RESEARCH_METHOD_VERSION`: research method contract version. Defaults to `0.1.0`.
- `DARWIN_ARTIFACT_ROOT`: root directory for runtime artifacts. Defaults to `artifacts`.
- `DARWIN_DATABASE_URL`: SQLAlchemy database URL. PostgreSQL with psycopg is the intended database, for example `postgresql+psycopg://darwin:darwin@localhost:5432/darwin`.

Do not commit real secrets or local `.env` files.

## CLI

Show CLI help:

```bash
darwin --help
```

Show foundation status:

```bash
darwin status
```

CLI smoke test:

```bash
darwin --help
darwin status
```

Check database connectivity:

```bash
darwin db-status
```

The database status command performs a read-only `select 1` connectivity check.

Research persistence smoke commands:

```bash
darwin research --help
darwin research create-run "Research question"
darwin research get-run <run-uuid-or-public-id>
```

These commands require a configured database and call the service layer directly.

## Tests

Run the deterministic foundation test suite:

```bash
pytest
```

The tests do not require a live PostgreSQL server.

## Migrations

Alembic is configured to use Darwin settings and SQLAlchemy metadata from `darwin.db.Base`.

Create a new migration after future model changes:

```bash
alembic revision --autogenerate -m "describe change"
```

Apply migrations:

```bash
alembic upgrade head
```

Inspect generated SQL without connecting to the database:

```bash
alembic upgrade head --sql
```

Phase 1.8B defines the first domain migration:

```bash
alembic upgrade head
```

The current migration creates the core research data model tables only. It does not provision a database or implement research workflows.

## Architectural Boundary

Darwin v0.1 is documented as a modular monolith with a single orchestrator. Phase 1.8B does not implement the orchestrator itself.

Current v0.1 persistence decisions:

- PostgreSQL is the primary persistent store.
- No separate vector database is introduced in v0.1.
- No graph database is introduced in v0.1.
- `pgvector` is not implemented in Phase 1.8A.
- No multi-agent architecture is introduced in v0.1.

The current documentation structure reserves directories for future architecture, method, runtime, data model, decisions, and benchmark documentation without populating speculative content.
