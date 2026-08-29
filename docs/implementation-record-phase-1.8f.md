# Phase 1.8F Implementation Record

## Objective

Implement Darwin's first external research acquisition layer for controlled source discovery, candidate audit history, conservative normalization/deduplication, and Source registration.

## Scope

Added a provider-agnostic acquisition boundary and persistence records for search/discovery results. The layer accepts explicit acquisition requests for existing research runs, calls one provider adapter, persists request/candidate provenance, registers accepted Sources through `ResearchService`, and exposes source IDs that can be supplied to the existing manual orchestrator.

## Provider Selected

Implemented `BraveSearchProvider` as the real provider adapter using `httpx` and environment-based credentials. Kept `FakeResearchProvider` for deterministic tests and local smoke checks.

## Files Changed

- `src/darwin/acquisition/__init__.py`
- `src/darwin/acquisition/errors.py`
- `src/darwin/acquisition/normalization.py`
- `src/darwin/acquisition/providers.py`
- `src/darwin/acquisition/schemas.py`
- `src/darwin/acquisition/service.py`
- `src/darwin/config/settings.py`
- `src/darwin/db/__init__.py`
- `src/darwin/db/models.py`
- `src/darwin/orchestration/schemas.py`
- `src/darwin/orchestration/service.py`
- `src/darwin/cli/app.py`
- `alembic/versions/0004_external_research_acquisition.py`
- `tests/conftest.py`
- `tests/test_acquisition_service.py`
- `tests/test_cli.py`
- `tests/test_config.py`
- `tests/test_migrations.py`
- `tests/test_research_orchestrator.py`
- `.env.example`
- `pyproject.toml`
- `README.md`
- `docs/runtime/external-research-acquisition.md`
- `docs/data_model/external-research-acquisition.md`
- `docs/method/research-method-v0.1.md`
- `docs/decisions/ADR-008-provider-agnostic-acquisition-audit.md`
- `docs/implementation-record-phase-1.8f.md`

## Schema and Migration

Created Alembic revision `0004_external_research_acquisition`.

Added tables:

- `research_acquisition_requests`
- `source_candidates`

Added enum types:

- `acquisition_status`
- `source_candidate_registration_status`

## Provider Contract

Providers implement `ResearchProvider.search(request) -> ProviderSearchResult`. Results preserve provider ID, optional provider request ID, original query, execution timestamp, status, candidates, warnings/errors, retry attempts, request count, usage/cost fields, provider metadata, and rate-limit metadata.

## Normalization

Candidate normalization trims locators, lowercases URL scheme and host, removes fragments, removes common tracking query parameters, sorts remaining query parameters, derives domain only when safe, and infers `WEB_PAGE` only for HTTP(S) locators.

Unknown metadata remains null/unknown.

## Deduplication

Deduplication is conservative and deterministic. Phase 1.8F deduplicates within a provider result by exact normalized locator and relies on `ResearchService` for existing exact Source reuse. It does not use fuzzy title matching or semantic merging.

## Security

Credentials are environment-only. `.env.example` documents `DARWIN_BRAVE_SEARCH_API_KEY` without a real value. Secret-shaped metadata keys are redacted before persistence.

## Tests

Added deterministic tests for request validation, provider success, timeout/error handling, partial results, provenance, normalization, deduplication, source boundary, failure behavior, secret redaction, transaction rollback, CLI fake-provider smoke, migration head/offline SQL, and orchestrator handoff.

## Live vs Fake Testing

The automated test suite uses `FakeResearchProvider`. A live Brave query requires `DARWIN_EXTERNAL_SEARCH_PROVIDER=brave` and `DARWIN_BRAVE_SEARCH_API_KEY`. No live provider result should be inferred from fake-provider tests.

## Documentation

Added runtime and data model docs for acquisition, updated the research method and README, and recorded ADR-008.

## Deviations

No intentional deviations from Phase 1.8F scope.

## Limitations

- No content fetching beyond the provider search API.
- No HTML extraction, PDF parsing, JavaScript rendering, or browser automation.
- No automatic Evidence creation from snippets.
- No automatic Claim creation.
- No semantic validation or confidence scoring.
- No scheduled/background research.
- No financial-market or exchange adapters.

## Deferred Functionality

Deferred to later phases:

- source content acquisition and extraction
- evidence capture from source content
- automated claim generation
- semantic contradiction detection
- source quality/reputation scoring
- recurring/autonomous research
- vector/graph retrieval systems
- recommendation workflows

## Phase Boundary Confirmation

No Phase 1.8G+ functionality was implemented.
