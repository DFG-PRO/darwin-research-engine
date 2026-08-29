# Phase 1.8G Implementation Record

## Objective

Implement the controlled foundation that turns a registered Source into fetched content, auditable snapshots, normalized content, deterministic segments, and explicitly selected Evidence records.

## Scope

Added provider-agnostic source content fetching, artifact-backed snapshot storage, deterministic HTML/text normalization, paragraph segmentation, and explicit segment/span evidence extraction.

## Files Changed

- `src/darwin/content/__init__.py`
- `src/darwin/content/artifacts.py`
- `src/darwin/content/errors.py`
- `src/darwin/content/fetchers.py`
- `src/darwin/content/hashing.py`
- `src/darwin/content/normalization.py`
- `src/darwin/content/schemas.py`
- `src/darwin/content/segmentation.py`
- `src/darwin/content/service.py`
- `src/darwin/config/settings.py`
- `src/darwin/db/__init__.py`
- `src/darwin/db/models.py`
- `src/darwin/cli/app.py`
- `alembic/versions/0005_source_content_acquisition.py`
- `tests/test_source_content_service.py`
- `tests/test_cli.py`
- `tests/test_config.py`
- `tests/test_migrations.py`
- `.env.example`
- `README.md`
- `docs/README.md`
- `docs/runtime/source-content-acquisition.md`
- `docs/runtime/research-orchestrator.md`
- `docs/method/evidence-extraction.md`
- `docs/method/research-method-v0.1.md`
- `docs/data_model/source-content-acquisition.md`
- `docs/decisions/ADR-009-source-content-artifact-snapshot-strategy.md`
- `docs/implementation-record-phase-1.8g.md`

## Schema and Migration

Created Alembic revision `0005_source_content_acquisition`.

Added tables:

- `source_content_snapshots`
- `source_content_segments`
- `evidence_extraction_records`

Added enum types:

- `source_fetch_status`
- `evidence_extraction_status`

## Fetcher

Implemented a `SourceFetcher` protocol, `HTTPSourceFetcher`, and deterministic `FakeSourceFetcher`. The HTTP fetcher uses `httpx`, HTTP/HTTPS only, explicit timeout, bounded retries, redirects, User-Agent, content-type allowlist, response-size limit, and explicit status mapping.

## Content Types

Supported:

- HTML/text pages
- plain text
- JSON-like text responses

Deferred:

- PDF
- JavaScript rendering
- browser automation
- OCR/images
- audio/video
- office documents

## Artifact Strategy

Raw and normalized content artifacts are written under `DARWIN_ARTIFACT_ROOT/source-content/<research_run_id>/<source_id>/<snapshot_id>/`. Paths are generated from UUIDs, traversal-checked, independent of remote filenames, and written through atomic replace.

## Normalization

HTML normalization removes script/style/noscript content and extracts readable text with the standard library HTML parser. Plain text normalization standardizes newlines and whitespace. No paraphrasing, summarization, or AI extraction is performed.

## Segmentation

Normalized text is split into deterministic paragraph segments. Each segment records order, identifier, locator, exact text, character/line offsets, and SHA-256 fingerprint.

## Evidence Extraction

Evidence extraction requires an explicit `SegmentExtractionRequest`. Full-segment or exact character-span selections are registered as `EvidenceType.EXCERPT` through `ResearchService`. Extraction records preserve Source, Snapshot, Segment, Evidence ID, selected text, fingerprint, locator, offsets, method version, status, and sanitized metadata.

## Security

Implemented protections for non-HTTP schemes, unsupported content types, oversized responses, safe redirect schemes, path traversal, arbitrary file writes, credential-shaped metadata redaction, and no shell/local-file provider behavior.

## Tests

Added deterministic tests for HTML/plain-text fetch, mocked HTTP success/timeout/error/redirect/unsupported/oversized/invalid scheme, snapshot history, repeated identical content, artifact root safety, artifact write rollback, normalization, segmentation, exact evidence extraction, oversized extraction rejection, no Claim creation, no automatic validation, source/run failure behavior, CLI smoke, and migration checks.

## Documentation

Created runtime, method, data model, ADR, and implementation record documentation. Updated README, docs index, research method, and orchestrator docs.

## ADRs

Created `ADR-009: Source Content Artifact and Snapshot Strategy`.

## Deviations

No intentional deviations from Phase 1.8G scope.

## Limitations

- No live web fetch is required or included in tests.
- No sophisticated article extraction.
- No semantic chunking.
- No automatic Evidence creation from fetched content.
- No automatic Claim creation.
- No automatic validation invocation from extraction.
- No crawler, browser, PDF, OCR, audio/video, or office-document pipeline.

## Deferred Functionality

Deferred to later phases:

- richer content extraction
- PDF and document parsing
- semantic evidence selection
- claim generation
- contradiction detection
- confidence scoring
- source reputation scoring
- scheduled/background research
- vector/graph retrieval systems
- recommendations

## Phase Boundary Confirmation

No Phase 1.8H+ functionality was implemented.
