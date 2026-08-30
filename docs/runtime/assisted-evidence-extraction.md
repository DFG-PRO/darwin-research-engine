# Assisted Evidence Extraction Runtime

Phase 1.9B adds `darwin.extraction` as a dedicated assisted extraction boundary.

## Request Lifecycle

`AssistedEvidenceExtractionService.propose_evidence(request)`:

1. Validates the `ResearchRun`.
2. Validates the `ResearchPlanItem` belongs to that run.
3. Validates the `Source`.
4. Validates the `SourceContentSnapshot` belongs to the run and source.
5. Loads selected segments by ids or bounded segment order range.
6. Enforces segment, candidate, per-segment character, and total character limits.
7. Calls the configured provider.
8. Validates strict candidate schema.
9. Validates exact grounding against stored segment text.
10. Persists the request and candidate history.

This flow does not create canonical Evidence.

## Provider Abstraction

Providers implement:

```text
propose_candidates(request, segments, limits) -> ProviderEvidenceExtractionResult
```

Core Darwin ships:

- `FakeEvidenceExtractionProvider`
- `OpenAIEvidenceExtractionProvider`

The fake provider is deterministic and supports success, timeout, error, and malformed-output modes for tests.

## Persistence

The runtime writes:

- `assisted_evidence_extraction_requests`
- `evidence_candidate_proposals`

Candidate records are append-oriented. Failed provider attempts are persisted as failed requests when request provenance is valid. Invalid grounded candidates remain auditable as `REJECTED_INVALID_GROUNDING`.

## Acceptance

`accept_candidate(candidate_id)`:

1. Loads the candidate and request.
2. Confirms the candidate is `VALIDATED`.
3. Reloads the canonical segment.
4. Revalidates snapshot/source/run provenance.
5. Revalidates exact offsets and excerpt.
6. Checks for a previously accepted duplicate grounded span.
7. Creates canonical Evidence through `ResearchService`.
8. Creates an `EvidenceExtractionRecord`.
9. Links candidate to Evidence.
10. Marks candidate `ACCEPTED`.

The same accepted candidate may be accepted again without duplicating Evidence.

## Rejection

`reject_candidate(candidate_id, reason)` marks a non-accepted candidate `REJECTED` and stores the rejection reason and timestamp. Rejected candidates are retained and cannot be accepted through the default transition.

## Transaction Ownership

Services flush but do not commit. Callers own transaction boundaries.

Acceptance runs the Evidence creation, extraction record creation, and candidate linkage inside a nested transaction. If Evidence or extraction-record persistence fails, no partial canonical Evidence remains and the candidate stays eligible.

## CLI

Commands:

```bash
darwin research propose-evidence --research-run-id <run> --research-plan-item-id <item> \
  --source-id <source> --snapshot-id <snapshot> --segment-id <segment> \
  --objective "..." --requirement "..." --provider fake

darwin research evidence-candidates
darwin research evidence-candidates --extraction-request-id <request>
darwin research accept-evidence <candidate-id>
darwin research reject-evidence <candidate-id> --reason "..."
```

CLI output shows candidate id, source, segment, excerpt, proposed evidence type, relevance, grounding status, and candidate status.

## Errors

Runtime errors include:

- `ExtractionValidationError`
- `ExtractionProviderError`
- `ExtractionProviderTimeout`
- `ExtractionConfigurationError`
- `EvidenceCandidateAcceptanceError`
- `EvidenceCandidateRejectionError`

Provider failure, malformed output, invalid relationships, invalid offsets, excerpt mismatch, and duplicate acceptance do not create canonical Evidence.

## Limits

Configured limits:

- `DARWIN_ASSISTED_EVIDENCE_EXTRACTION_MAX_SEGMENTS`
- `DARWIN_ASSISTED_EVIDENCE_EXTRACTION_MAX_CANDIDATES`
- `DARWIN_ASSISTED_EVIDENCE_EXTRACTION_MAX_SEGMENT_CHARS`
- `DARWIN_ASSISTED_EVIDENCE_EXTRACTION_MAX_TOTAL_REQUEST_CHARS`

Darwin fails clearly when limits are exceeded. It does not silently truncate content in ways that would invalidate offsets.

## Security

Source content is untrusted data. It has no ability to override system instructions, call tools, fetch URLs, run searches, execute shell commands, or query the database.

Provider credentials are read from environment variables only. Secrets and authentication headers are not persisted or printed.
