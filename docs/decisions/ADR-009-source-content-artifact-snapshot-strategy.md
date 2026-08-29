# ADR-009: Source Content Artifact and Snapshot Strategy

## Status

Accepted

## Context

Phase 1.8G introduces source content fetching and exact evidence extraction. Darwin needs historical fetch auditability without storing arbitrarily large raw bodies in ordinary relational columns.

## Decision

Persist fetch metadata, status, fingerprints, artifact references, deterministic segments, and extraction audit records in PostgreSQL. Store raw and normalized content artifacts under `DARWIN_ARTIFACT_ROOT` using generated UUID-based paths.

Use append-only snapshots for every fetch attempt. Use SHA-256 fingerprints for exact raw content, normalized content, segments, and evidence excerpts.

## Consequences

- Darwin can retain multiple snapshots for the same Source over time.
- Raw content size is controlled by configuration and stored outside normal relational columns.
- Evidence can trace to an exact Source, Snapshot, Segment, and selected span.
- Artifact paths are deterministic, traversal-checked, and independent of remote filenames.
- This decision does not introduce crawling, browser automation, PDF extraction, AI summarization, automatic claim generation, semantic extraction, vector storage, graph storage, or autonomous research.
