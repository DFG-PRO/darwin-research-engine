# ADR-008: Provider-Agnostic Acquisition Audit Boundary

## Status

Accepted

## Context

Phase 1.8F introduces external source discovery. Darwin needs provider replacement flexibility and persistent acquisition history without allowing provider output to bypass evidence, claim, or validation boundaries.

## Decision

Implement external acquisition as a provider-agnostic service with a small `ResearchProvider` protocol. Persist every acquisition request and source candidate as audit records. Register accepted source candidates through `ResearchService` so Source creation remains centralized.

Implement one real provider adapter, `BraveSearchProvider`, using `httpx` and environment-provided credentials. Keep `FakeResearchProvider` as deterministic infrastructure for tests and local smoke checks.

## Consequences

- Core Darwin does not depend directly on one search vendor.
- Provider query, timing, status, warnings, errors, rate/cost metadata, candidates, and source registration outcomes are auditable.
- Provider snippets remain source-candidate material and are not automatically promoted to Evidence.
- Candidates are deduplicated only by conservative deterministic signals.
- Darwin v0.1 remains a modular monolith with a single orchestrator and no multi-agent architecture.
- This decision does not introduce autonomous research, crawling, content extraction, semantic validation, confidence scoring, recommendations, vector databases, graph databases, or `pgvector`.
