# Darwin Research & Intelligence Engine

Darwin v0.1 is the initial foundation for a research and intelligence engine intended to preserve traceable evidence, validated knowledge, historical context, confidence, outcomes, errors, contradictions, assumptions, and decisions over time.

Current status: **Phase 1.8I Research MVP benchmark and Phase 1.8 closure assessment**. This repository provides the technical base, persistent research schema, lifecycle persistence services, deterministic structural claim validation, a supplied-material research orchestrator, controlled external source discovery, explicit source-content snapshot/segment/evidence extraction, caller-supplied claim construction, evidence-grounded structured synthesis records, and a reproducible supplied-material benchmark. It does not implement autonomous research, crawling, semantic claim validation, automatic claim generation, confidence scoring, recommendation systems, memory retrieval, or domain intelligence features.

## What Exists

- Python 3.12+ project using a `src/` layout.
- Centralized environment-driven configuration.
- Consistent application logging setup.
- PostgreSQL-oriented SQLAlchemy 2.x engine, session, and declarative metadata foundation.
- Alembic migration environment wired to Darwin settings and SQLAlchemy metadata.
- Core SQLAlchemy research data model and first Alembic schema migration.
- Minimal research persistence service layer for lifecycle and traceability operations.
- Deterministic claim validation service and auditable validation history.
- Deterministic supplied-material research orchestrator and synthesis records.
- Provider-agnostic external source discovery with auditable acquisition history.
- Controlled source content fetching, artifact snapshots, deterministic segmentation, and explicit Evidence extraction.
- Explicit caller-supplied evidence-to-claim construction with append-only construction audit records.
- Structured synthesis records that preserve claim evidence provenance, conclusion dependencies, validation state, and deterministic warnings.
- Phase 1.8I supplied-material Research MVP benchmark artifacts and closure documentation.
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
- `DARWIN_EXTERNAL_SEARCH_PROVIDER`: external source discovery provider. Defaults to `fake`; supported values are `fake` and `brave`.
- `DARWIN_EXTERNAL_SEARCH_TIMEOUT_SECONDS`: HTTP timeout for external search providers. Defaults to `10`.
- `DARWIN_EXTERNAL_SEARCH_MAX_RETRIES`: bounded retry count for external search providers. Defaults to `1`.
- `DARWIN_EXTERNAL_SEARCH_USER_AGENT`: User-Agent for HTTP search providers. Defaults to `DarwinResearchEngine/0.1`.
- `DARWIN_BRAVE_SEARCH_API_KEY`: required only when `DARWIN_EXTERNAL_SEARCH_PROVIDER=brave`.
- `DARWIN_SOURCE_FETCH_TIMEOUT_SECONDS`: HTTP timeout for source content fetches. Defaults to `10`.
- `DARWIN_SOURCE_FETCH_MAX_RETRIES`: bounded retry count for source content fetches. Defaults to `1`.
- `DARWIN_SOURCE_FETCH_USER_AGENT`: User-Agent for HTTP source content fetches. Defaults to `DarwinResearchEngine/0.1`.
- `DARWIN_SOURCE_FETCH_MAX_BYTES`: maximum raw bytes stored for one source fetch. Defaults to `1000000`.
- `DARWIN_SOURCE_CONTENT_RETRIEVAL_METHOD_VERSION`: source retrieval method version. Defaults to `source-fetch-http-1.8g`.
- `DARWIN_SOURCE_CONTENT_NORMALIZATION_METHOD_VERSION`: normalization method version. Defaults to `html-text-normalization-1.8g`.
- `DARWIN_EVIDENCE_EXTRACTION_METHOD_VERSION`: extraction method version. Defaults to `segment-extraction-1.8g`.
- `DARWIN_EVIDENCE_EXCERPT_MAX_CHARS`: maximum characters in one extracted Evidence excerpt. Defaults to `4000`.
- `DARWIN_CLAIM_CONSTRUCTION_METHOD_VERSION`: explicit claim construction method version. Defaults to `manual-explicit-claim-construction-1.8h`.
- `DARWIN_STRUCTURED_SYNTHESIS_METHOD_VERSION`: structured synthesis method version. Defaults to `structured-synthesis-1.8h`.
- `DARWIN_CLAIM_STATEMENT_MAX_CHARS`: maximum characters in one constructed Claim statement. Defaults to `2000`.

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
darwin research validate-claim <claim-uuid>
darwin research acquire "search query" --research-run-id <run-uuid> --provider fake
darwin research fetch-source <source-uuid> --research-run-id <run-uuid> --fetcher fake
darwin research source-content <snapshot-uuid>
darwin research extract-evidence <segment-uuid> --research-run-id <run-uuid>
darwin research construct-claim claim-input.json
darwin research claim <claim-uuid>
darwin research synthesize <run-uuid-or-public-id>
darwin research run-manual tests/fixtures/manual_research_complete.json
```

These commands require a configured database and call the service layer directly.

`darwin research acquire` discovers source candidates and registers accepted Sources. Provider snippets remain acquisition audit material only; they are not automatically Evidence, Claims, or Conclusions.

`darwin research fetch-source` fetches a registered Source and writes raw/normalized artifacts below `DARWIN_ARTIFACT_ROOT`. `darwin research extract-evidence` only creates Evidence from an explicitly selected segment or span; it does not create Claims.

`darwin research construct-claim` requires a caller-supplied claim statement and explicit evidence selections. Darwin links the claim to evidence, writes a construction audit record, and runs structural validation. It does not infer the claim statement from evidence.

`darwin research claim` shows a persisted claim with evidence/source/snapshot/segment provenance. `darwin research synthesize` creates an append-only structured synthesis record for a research run.

## Tests

Run the deterministic foundation test suite:

```bash
pytest
```

The tests do not require a live PostgreSQL server.

Run the Phase 1.8I benchmark regression tests:

```bash
pytest tests/test_phase_1_8i_benchmark.py
```

Run the benchmark directly:

```bash
python benchmarks/phase-1.8i/run_benchmark.py
```

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

The current migrations create the core research data model, source lineage fields, claim validation evaluations, explicit human validation events, research framings, research plan items, synthesis records, acquisition requests, source candidates, source content snapshots, source content segments, evidence extraction records, claim construction audit records, claim construction evidence selections, and conclusion-to-claim links. They do not provision a database, crawl content, or implement autonomous research.

## Architectural Boundary

Darwin v0.1 is documented as a modular monolith with a single orchestrator. Phase 1.8E implemented the first deterministic supplied-material orchestrator. Phase 1.8F added a provider-agnostic external acquisition layer that can feed registered Sources into the existing manual boundary. Phase 1.8G added explicit content snapshots and segment-based Evidence extraction. Phase 1.8H added explicit evidence-to-claim construction and deterministic structured synthesis. Phase 1.8I adds benchmark, audit, and closure records.

Current v0.1 persistence decisions:

- PostgreSQL is the primary persistent store.
- No separate vector database is introduced in v0.1.
- No graph database is introduced in v0.1.
- `pgvector` is not implemented in Phase 1.8A.
- No multi-agent architecture is introduced in v0.1.
- External acquisition does not turn provider results into validated evidence or truth.
- Fetching content does not automatically create Evidence, Claims, validation, conclusions, or truth.
- Evidence-to-claim construction uses caller-supplied claim text only.
- Structured synthesis does not generate autonomous conclusions or recommendations.

The authoritative Phase 1.8 technical record is `docs/phases/phase-1.8/PHASE-1.8-MASTER.md`. The closure assessment is `docs/phases/phase-1.8/PHASE-1.8-CLOSURE.md`.
