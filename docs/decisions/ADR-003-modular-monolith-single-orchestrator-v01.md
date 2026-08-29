# ADR-003: Modular Monolith and Single Orchestrator for v0.1

## Status

Accepted

## Context

Darwin v0.1 needs a foundation that can evolve without premature distribution complexity. Phase 1.8A should not introduce multiple services, multi-agent coordination, or speculative runtime subsystems.

## Decision

Darwin v0.1 is a modular monolith with a single orchestrator. Phase 1.8A establishes only the repository, configuration, logging, database, migration, CLI, testing, and documentation foundation needed to support that direction later.

## Consequences

- Darwin v0.1 does not use a multi-agent architecture.
- Runtime boundaries should remain modular inside one application before any future service extraction is considered.
- No orchestrator implementation or research workflow is added in Phase 1.8A.
