# ADR-002: PostgreSQL as Primary Persistent Store

## Status

Accepted

## Context

Darwin v0.1 needs a durable relational persistence foundation that can later support traceable evidence, historical records, claims, conclusions, outcomes, contradictions, assumptions, benchmarks, and context changes.

## Decision

PostgreSQL is Darwin v0.1's primary persistent store. Phase 1.8A configures SQLAlchemy 2.x, psycopg, declarative metadata, session management, and Alembic around a PostgreSQL database URL.

## Consequences

- Future domain tables can share one SQLAlchemy metadata foundation for migration autogeneration.
- The current phase defines no Darwin domain tables.
- No separate vector database or graph database is introduced by this decision.
