# Assisted Claim Construction Runtime

Phase 1.9C adds `darwin.claim_assistance` as a dedicated assisted Claim construction boundary.

## Request Lifecycle

`AssistedClaimConstructionService.propose_claims(request)`:

1. Validates the `ResearchRun`.
2. Validates the `ResearchPlanItem` belongs to that run.
3. Loads the requested canonical Evidence records.
4. Confirms all Evidence belongs to the run and has source provenance.
5. Enforces Evidence, candidate, Claim text, qualifier, and assumption limits.
6. Calls the configured provider.
7. Validates strict candidate schema.
8. Validates candidate Evidence ids against the request.
9. Persists the request and candidate history.

This flow does not create canonical Claims.

## Provider Abstraction

Providers implement:

```text
propose_claims(request, evidence, limits) -> ProviderClaimConstructionResult
```

Core Darwin ships:

- `FakeClaimConstructionProvider`
- `OpenAIClaimConstructionProvider`

The fake provider is deterministic and supports success, timeout, error, and malformed-output modes for tests.

## Persistence

The runtime writes:

- `assisted_claim_construction_requests`
- `claim_candidate_proposals`
- `claim_candidate_evidence`

Candidate records are append-oriented. Failed provider attempts are persisted as failed requests when request provenance is valid. Invalid request context fails before provider execution.

## Acceptance

`accept_claim_candidate(candidate_id)`:

1. Loads the candidate, request, and candidate Evidence links.
2. Confirms the candidate is `VALIDATED`.
3. Revalidates canonical Evidence existence and ResearchRun provenance.
4. Confirms candidate Evidence ids were present in the original request.
5. Checks for a previously accepted duplicate statement and Evidence-role set.
6. Creates canonical Claim through `ResearchService`.
7. Creates ClaimEvidence links with the candidate's evidence roles.
8. Creates a `ClaimConstructionRecord` and `ClaimConstructionEvidence` rows.
9. Links the candidate to the Claim.
10. Marks candidate `ACCEPTED`.

The same accepted candidate may be accepted again without duplicating a Claim.

## Rejection

`reject_claim_candidate(candidate_id, reason)` marks a non-accepted candidate `REJECTED` and stores the rejection reason and timestamp. Rejected candidates are retained and cannot be accepted through the default transition.

## Transaction Ownership

Services flush but do not commit. Callers own transaction boundaries.

Acceptance runs Claim creation, ClaimEvidence linkage, construction audit rows, and candidate linkage inside a nested transaction. If any canonical linkage write fails, no partial Claim remains and the candidate stays eligible.

## CLI

Commands:

```bash
darwin research propose-claims --research-run-id <run> --research-plan-item-id <item> \
  --evidence-id <evidence> --objective "..." --instruction "..." --provider fake

darwin research claim-candidates
darwin research claim-candidates --construction-request-id <request>
darwin research accept-claim <candidate-id>
darwin research reject-claim <candidate-id> --reason "..."
```

CLI output shows candidate id, status, claim id when accepted, proposed type, claim text, Evidence role links, qualifiers, and warnings.

## Errors

Runtime errors include:

- `ClaimCandidateValidationError`
- `ClaimConstructionProviderError`
- `ClaimConstructionProviderTimeout`
- `ClaimConstructionConfigurationError`
- `ClaimCandidateAcceptanceError`
- `ClaimCandidateRejectionError`

Provider failure, malformed output, invalid relationships, unsupported Evidence ids, non-atomic Claim text, recommendation language, and duplicate accepted candidates do not create canonical Claims.

## Limits

Configured limits:

- `DARWIN_ASSISTED_CLAIM_CONSTRUCTION_MAX_EVIDENCE_ITEMS`
- `DARWIN_ASSISTED_CLAIM_CONSTRUCTION_MAX_EVIDENCE_CHARS`
- `DARWIN_ASSISTED_CLAIM_CONSTRUCTION_MAX_CANDIDATES`
- `DARWIN_ASSISTED_CLAIM_CONSTRUCTION_MAX_CLAIM_CHARS`
- `DARWIN_ASSISTED_CLAIM_CONSTRUCTION_MAX_QUALIFIERS`
- `DARWIN_ASSISTED_CLAIM_CONSTRUCTION_MAX_ASSUMPTIONS`

Darwin fails clearly when limits are exceeded.

## Security

Evidence statements are untrusted data. They cannot override system instructions, call tools, fetch URLs, create sources, run validation, execute shell commands, query the database, or assign confidence.

Provider credentials are read from environment variables only. Secrets and authentication headers are not persisted or printed.
