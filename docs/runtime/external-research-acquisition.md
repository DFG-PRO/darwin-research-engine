# External Research Acquisition

Phase 1.8F adds Darwin's first controlled external source discovery layer.

## Architecture

External research enters Darwin through a provider-agnostic acquisition boundary:

1. Caller supplies an explicit `AcquisitionRequest`.
2. A `ResearchProvider` adapter searches for source candidates.
3. Darwin persists the acquisition request and provider result.
4. Candidates are normalized and conservatively deduplicated.
5. Non-duplicate candidates with known source type are registered through `ResearchService`.

The acquisition layer does not run recursive searches, generate research plans, extract evidence, infer claims, or validate source truth.

## Provider Boundary

Providers implement:

```text
ResearchProvider.search(request) -> ProviderSearchResult
```

The result preserves provider ID, optional provider request ID, original query, execution timestamp, status, warnings/errors, retry attempts, cost/rate metadata, and returned source candidates.

The implemented real adapter is `BraveSearchProvider`, configured through environment variables and plain HTTP via `httpx`. `FakeResearchProvider` is deterministic and exists for tests and local smoke checks.

## Request Contract

Acquisition requests include:

- `research_run_id`
- `query`
- optional `category`
- optional requested source types
- optional freshness window
- optional domain constraints
- `result_limit`
- request metadata

The schema remains generic and does not encode financial, arbitrage, exchange, or market-specific concepts.

## Provenance

Acquisition history is persisted in `research_acquisition_requests` and `source_candidates`.

This preserves:

- what was searched
- which provider ran the search
- when it ran
- supplied constraints
- status, warnings, and errors
- candidates returned
- candidate-to-source registration outcomes
- cost/rate metadata when supplied

## Normalization

Darwin normalizes only deterministic URL variance:

- trims whitespace
- lowercases URL scheme and host
- removes URL fragments
- removes common tracking query parameters such as `utm_*`, `fbclid`, `gclid`, and `msclkid`
- sorts remaining query parameters
- removes trailing slash from non-root paths

Unknown metadata remains unknown/null. Darwin does not invent publication dates, source types, publishers, or source identities.

## Deduplication

Deduplication is conservative. Phase 1.8F uses exact normalized locator matching within one acquisition result and existing exact source matching through `ResearchService`.

It does not perform fuzzy title matching, semantic deduplication, clustering, or source reputation scoring.

## Failure Model

Acquisitions have explicit statuses:

- `SUCCESS`
- `PARTIAL`
- `FAILED`

Provider timeouts and provider errors are captured as failed acquisition records. Partial results remain auditable and can still register returned candidates. A failed acquisition does not mark the research run failed or create empty successful output.

## Security

Credentials are environment-only. `DARWIN_BRAVE_SEARCH_API_KEY` is a secret setting and is not persisted. Metadata keys that look secret-shaped are redacted before persistence.

The layer does not execute shell commands, read arbitrary local files, crawl websites, parse PDFs, render JavaScript, or bypass robots/access controls.

## Rate and Cost Awareness

Provider result fields allow request count, usage units, estimated/actual cost, retry attempts, and rate-limit metadata. Unknown values remain null or empty.

## Orchestration Integration

Acquisition can run separately and register Sources. `ResearchOrchestrator.run_manual` can receive existing acquired source IDs through `acquired_source_ids`, preserving the supplied-material workflow.

Discovered sources do not satisfy plan items and do not become Evidence unless explicit evidence is supplied later.

## Limitations

- No general crawler or content extraction.
- No automatic evidence creation from snippets.
- No automatic claim creation.
- No LLM calls.
- No autonomous research loop.
- No live provider test was performed unless credentials are present and explicitly used during verification.
