# Phase 1.9C Implementation Record

## Objective

Implement Darwin's controlled Assisted Claim Construction layer. The layer turns canonical Evidence selected for a ResearchPlanItem into auditable Claim candidate proposals, then requires explicit acceptance before canonical Claims and ClaimEvidence links are created.

## Baseline

Verified before modification:

- repository path: `/Volumes/BLACKBOX/2 CODE PROJECTS/Darwin Research Engine/darwin-research-engine`
- branch: `main`
- tag `phase-1.9b` exists
- tag `phase-1.9b` matched the starting HEAD
- Phase 1.8 master documentation exists
- Phase 1.9A and 1.9B implementation records exist
- migration head before work: `0008_assisted_evidence_extraction`
- baseline tests: `124 passed`

## Scope

Implemented:

- dedicated `darwin.claim_assistance` module
- strict assisted claim construction request schema
- strict Claim candidate proposal schema
- provider-agnostic Claim construction provider protocol
- deterministic fake provider
- minimal optional OpenAI adapter
- request, candidate, and candidate Evidence-link persistence
- canonical Evidence provenance validation
- explicit candidate acceptance into canonical Claim and ClaimEvidence
- explicit candidate rejection
- duplicate accepted-candidate prevention
- orchestrator helper methods
- CLI commands
- migration `0009_assisted_claim_construction`
- deterministic tests and documentation

## Files

Created:

- `src/darwin/claim_assistance/__init__.py`
- `src/darwin/claim_assistance/errors.py`
- `src/darwin/claim_assistance/providers.py`
- `src/darwin/claim_assistance/schemas.py`
- `src/darwin/claim_assistance/service.py`
- `alembic/versions/0009_assisted_claim_construction.py`
- `tests/test_assisted_claim_construction.py`
- `docs/method/assisted-claim-construction.md`
- `docs/runtime/assisted-claim-construction.md`
- `docs/implementation-record-phase-1.9c.md`

Modified:

- `.env.example`
- `README.md`
- `docs/README.md`
- `docs/data_model/core-research-data-model.md`
- `src/darwin/cli/app.py`
- `src/darwin/config/settings.py`
- `src/darwin/db/models.py`
- `src/darwin/orchestration/service.py`
- `tests/test_cli.py`
- `tests/test_migrations.py`
- `tests/test_models.py`

## Schema And Migration

Migration `0009_assisted_claim_construction` adds:

- `assisted_claim_construction_requests`
- `claim_candidate_proposals`
- `claim_candidate_evidence`
- `assisted_claim_construction_request_status`
- `claim_candidate_status`
- `claim_candidate_acceptance_mode`

Migrations `0001` through `0008` were not modified.

## Claim Construction Architecture

`AssistedClaimConstructionService` owns the lifecycle:

```text
request -> provider Claim candidates -> schema/provenance validation
-> persisted candidates -> explicit accept/reject
```

Canonical Claims are still created only through `ResearchService.register_claim()`.

## Candidate Schema

Candidates include candidate key, proposed claim text/type, supporting Evidence ids, contradicting Evidence ids, contextual Evidence ids, temporal scope, qualifiers, assumptions, construction rationale, provider warnings, and construction method version.

Extra provider fields are forbidden.

## Evidence-Grounded Invariant

Every accepted Claim must be grounded in canonical Evidence. The provider cannot supply arbitrary URLs, canonical Claim ids, Conclusions, recommendations, validation states, confidence scores, or unsupported factual content with no Evidence id.

Acceptance revalidates that candidate Evidence links exist, belong to the same ResearchRun, and were in the original request.

## Provider Design

The core protocol is:

```text
ClaimConstructionProvider.propose_claims(request, evidence, limits)
```

The deterministic fake provider supports success, timeout, provider error, and malformed structured output simulation. The optional OpenAI adapter follows the Phase 1.9A/1.9B environment/provider pattern and treats Evidence statements as untrusted data.

## Acceptance And Rejection

Acceptance requires `VALIDATED` status, revalidates Evidence provenance, checks duplicate accepted candidates with the same statement and Evidence-role set, creates Claim, creates ClaimEvidence links, creates a `ClaimConstructionRecord`, creates `ClaimConstructionEvidence` rows, links candidate to Claim, and marks the candidate `ACCEPTED`.

Rejection requires a reason, preserves the candidate, and stores rejection timestamp/reason. Rejected candidates cannot be accepted by the default transition.

## Validation Boundary

Assisted Claim acceptance does not run `ClaimValidationService`. Accepted Claims remain `PROPOSED`, and validation evaluations remain absent until an explicit validation command or service call runs later.

## Provenance

Assisted claim construction records preserve ResearchRun, ResearchPlanItem, submitted Evidence ids, provider/model/response id, method/prompt/schema versions, validation results, candidate state, Evidence-role links, and acceptance/rejection metadata.

Accepted Claims preserve the usual Claim, ClaimEvidence, ClaimConstructionRecord, and ClaimConstructionEvidence provenance.

## Security

Evidence statements are untrusted data. They cannot grant tool, system, acquisition, shell, database, validation, confidence-scoring, or policy-changing privileges. Provider credentials are environment-only and are not persisted.

## Tests And Results

Added deterministic tests for valid/invalid requests, request context failures, fake provider behavior, provider failures, malformed output, duplicate candidate keys, unsupported Evidence ids, excessive candidates, overlong and recommendation-like claims, candidate persistence, acceptance, validation boundary preservation, revalidation, rollback, duplicate accepted candidates, rejection, prompt-injection-like Evidence text, and compatibility with manual claim construction.

Verification results:

- full pytest: `137 passed`
- assisted claim construction tests: `11 passed`
- CLI tests: `9 passed`
- model tests: `6 passed`
- migration tests: `9 passed`
- assisted evidence, planner, benchmark, and claim construction regression slice: `31 passed`
- claim validation regression tests: `11 passed`
- acquisition/content/synthesis/orchestration regression slice: `41 passed`
- CLI smoke: `darwin --help` and `DARWIN_ENV=test darwin status` passed
- assisted Claim CLI smoke: `tests/test_cli.py::test_assisted_claim_cli_propose_list_accept` passed as part of CLI tests
- Alembic offline upgrade head: passed
- Alembic offline downgrade `0009_assisted_claim_construction:0008_assisted_evidence_extraction`: passed
- `git diff --check`: passed

## Docs

Created:

- `docs/method/assisted-claim-construction.md`
- `docs/runtime/assisted-claim-construction.md`

Updated:

- README
- docs index
- core data model docs

## ADRs

No ADR was added. Phase 1.9C extends the existing modular monolith and provider-agnostic boundaries without a new architectural decision.

## Limitations

Live provider Claim construction was not verified unless credentials are supplied in a later environment. The fake provider is the deterministic test authority. The OpenAI adapter is intentionally minimal.

## Deferred Work

Deferred:

- richer provider schema export
- live-provider benchmark
- candidate review UI
- bulk review
- claim quality scoring
- automatic validation
- autonomous downstream research

## Boundary Confirmation

No Phase 1.9D+ functionality was implemented.

Claim proposal creates no canonical Claims until explicit acceptance.

Claim proposal does not validate Claims, synthesize research, launch acquisition, fetch content, create Sources, create Evidence, create Conclusions, assign confidence, or produce recommendations.

Manual Claim construction remains supported through the existing construction service.

No autonomous acquisition or autonomous research loop was implemented.

No persistent files outside the Darwin repository were modified.
