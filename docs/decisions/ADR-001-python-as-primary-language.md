# ADR-001: Python as Primary Language

## Status

Accepted

## Context

Phase 1.8A requires a clean, production-oriented repository foundation for Darwin v0.1 without implementing later research or intelligence features.

## Decision

Python 3.12+ is Darwin's primary application language for v0.1. The repository uses a `src/` layout, Typer for the CLI, Pydantic Settings for centralized configuration, SQLAlchemy for database access, Alembic for migrations, and pytest for deterministic foundation tests.

## Consequences

- Package imports are isolated from the repository root through the `src/` layout.
- The foundation aligns with Python's mature ecosystem for CLI, configuration, database access, migrations, and testing.
- This decision does not implement Phase 1.8B+ research workflows, evidence systems, validation systems, or domain intelligence behavior.
