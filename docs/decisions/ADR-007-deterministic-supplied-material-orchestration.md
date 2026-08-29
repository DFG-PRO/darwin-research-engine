# ADR-007: Deterministic Supplied-Material Orchestration

## Status

Accepted

## Context

Phase 1.8E introduces Darwin's first end-to-end research workflow, but external research collection and AI reasoning remain deferred. The system needs an auditable method boundary before integrating future research tools.

## Decision

Implement one deterministic `ResearchOrchestrator` that operates only on caller-supplied material. Persist framing, plan items, and synthesis records as first-class auditable database records. Use existing research persistence and claim validation services rather than duplicating their rules.

## Consequences

- Darwin can execute a complete supplied-material research workflow without web access, LLM calls, or external APIs.
- Method outputs are structured and versioned through `DARWIN_RESEARCH_METHOD_VERSION`.
- Framing, planning, validation, and synthesis state remain auditable.
- The v0.1 modular monolith and single-orchestrator architecture remain intact.
- This decision does not introduce autonomous research, multi-agent behavior, recommendations, semantic reasoning, or confidence scoring.
