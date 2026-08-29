# ADR-005: Core Research Data Model Foundation

## Status

Accepted

## Context

Phase 1.8B introduces Darwin's first persistent domain schema. Darwin needs provenance-first storage for bounded research runs, sources, evidence, claims, claim/evidence semantics, and conclusions while preserving the v0.1 architecture decisions from Phase 1.8A.

## Decision

Implement the Phase 1.8B research data model as SQLAlchemy ORM models backed by a PostgreSQL Alembic migration.

The model uses UUID-compatible primary keys, explicit enum-backed statuses and relationship semantics, timezone-aware timestamps, relational provenance links, nullable confidence fields, and PostgreSQL JSONB only for flexible metadata/context payloads.

## Consequences

- Evidence is attributable to a source through a required foreign key.
- Claims remain separate from evidence.
- Support, contradiction, contextualization, and related evidence relationships are represented explicitly in `claim_evidence`.
- Confidence can be stored when provided, but no confidence calculation is introduced.
- No research pipeline, extraction engine, validation logic, recommendation logic, vector store, graph store, pgvector usage, multi-agent system, or orchestrator runtime is introduced by this decision.
