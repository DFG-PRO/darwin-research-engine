# Source Content Acquisition

Phase 1.8G adds a controlled pipeline from registered Source to fetched content, content snapshot, normalized segments, and explicitly selected Evidence.

## Fetch Architecture

Content fetching starts from a registered `Source`. Callers submit a `SourceFetchRequest` with:

- `research_run_id`
- `source_id`
- optional canonical locator, which must match the registered Source locator
- optional timeout
- request metadata

The service verifies the research run and Source before fetching. It does not fetch arbitrary unrelated URLs.

## Fetcher Boundary

Fetchers implement:

```text
SourceFetcher.fetch(request) -> FetchResult
```

The concrete HTTP fetcher uses `httpx`. It has explicit timeout, bounded retries, redirect handling, User-Agent, response size limit, content-type checks, and clear status mapping.

`FakeSourceFetcher` is deterministic and used for tests and local smoke checks.

## Supported Content Types

Phase 1.8G supports:

- HTML/text web pages
- plain text
- JSON-like text API responses

Unsupported binary content is recorded as `UNSUPPORTED_CONTENT_TYPE`.

## Artifact Storage

Raw and normalized content are written below `DARWIN_ARTIFACT_ROOT`:

```text
source-content/<research_run_id>/<source_id>/<snapshot_id>/raw.bin
source-content/<research_run_id>/<source_id>/<snapshot_id>/normalized.txt
```

Remote filenames are never trusted. Paths are generated from UUIDs, checked for traversal, and written atomically through a temporary file in the target directory.

## Snapshots and History

Each fetch attempt creates an append-only `source_content_snapshots` row. Historical snapshots are not overwritten. If identical content is fetched again, Darwin records a second snapshot with the same content fingerprint.

Snapshot records preserve requested/final locator, fetch status, timestamps, response status, content type, fingerprints, body sizes, artifact paths, method versions, warnings/errors, and sanitized metadata.

## Normalization

HTML normalization removes obvious script, style, and noscript content, then extracts readable text. Plain text normalization standardizes newlines and whitespace. Darwin does not rewrite, paraphrase, summarize, or perform AI extraction.

Normalization version is recorded with each successful snapshot.

## Segmentation

Normalized text is segmented deterministically by paragraphs. Each `source_content_segments` row preserves snapshot ID, source ID, stable segment identifier/order, exact text, locator, character offsets, line offsets, and SHA-256 fingerprint.

## Evidence Extraction

Evidence extraction is explicit. A caller selects either:

- a full segment
- an exact character span within a segment

The selected text is registered through `ResearchService.register_evidence` as an `EXCERPT`. The extraction record links the resulting Evidence to Source, Snapshot, Segment, selection locator, offsets, method version, and fingerprint.

## Security and Failure Model

The HTTP fetcher rejects non-HTTP(S) locators, unsupported binary content, oversized responses, unsafe redirect schemes, and access-denied responses. It does not bypass paywalls, login gates, robots controls, or access restrictions.

Failures are represented as snapshot history where possible. Artifact write failures raise explicitly and roll back DB records when the caller uses a transaction.

## Limitations

- No browser automation.
- No JavaScript rendering.
- No crawler or recursive URL traversal.
- No PDF parsing.
- No OCR, image understanding, audio/video transcription, or office document extraction.
- No LLM calls.
- No semantic evidence extraction.
- No automatic claim generation or validation.
