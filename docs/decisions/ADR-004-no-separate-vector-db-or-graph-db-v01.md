# ADR-004: No Separate Vector DB or Graph DB in v0.1

## Status

Accepted

## Context

Darwin's long-term requirements include traceability, validation, confidence tracking, and retrievable historical memory. Phase 1.8A must not make those requirements harder, but it also must not implement future retrieval or knowledge systems.

## Decision

Darwin v0.1 will not use a separate vector database or graph database. PostgreSQL remains the primary persistent store for v0.1.

Phase 1.8A does not implement pgvector.

## Consequences

- There is no vector retrieval subsystem in Phase 1.8A.
- There is no graph persistence subsystem in Phase 1.8A.
- Avoiding separate data stores keeps the v0.1 foundation simpler while preserving room for future persistence decisions through later ADRs.
