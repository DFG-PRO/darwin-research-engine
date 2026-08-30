# Phase 1.9B Implementation Record

## Objective

Implement Darwin's controlled Assisted Evidence Extraction layer. The layer turns a ResearchPlanItem and stored SourceContentSegments into auditable evidence candidate proposals, then requires explicit acceptance before canonical Evidence is created.

## Baseline

Verified before modification:

- repository path: `/Volumes/BLACKBOX/2 CODE PROJECTS/Darwin Research Engine/darwin-research-engine`
- branch: `main`
- tag `phase-1.9a` exists
- Phase 1.8 master documentation exists
- Phase 1.9A implementation record exists
- migration head before work: `0007_research_planning`
- baseline tests: `110 passed`

## Scope

Implemented:

- dedicated `darwin.extraction` module
- strict assisted extraction request schema
- strict evidence candidate proposal schema
- provider-agnostic extraction provider protocol
- deterministic fake provider
- minimal optional OpenAI adapter
- request and candidate persistence
- exact excerpt/offset grounding validation
- explicit candidate acceptance into canonical Evidence
- explicit candidate rejection
- duplicate acceptance prevention
- orchestrator helper methods
- CLI commands
- migration `0008_assisted_evidence_extraction`
- deterministic tests and documentation

## Files

Created:

- `src/darwin/extraction/__init__.py`
- `src/darwin/extraction/errors.py`
- `src/darwin/extraction/providers.py`
- `src/darwin/extraction/schemas.py`
- `src/darwin/extraction/service.py`
- `alembic/versions/0008_assisted_evidence_extraction.py`
- `tests/test_assisted_evidence_extraction.py`
- `docs/method/assisted-evidence-extraction.md`
- `docs/runtime/assisted-evidence-extraction.md`
- `docs/implementation-record-phase-1.9b.md`

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

Migration `0008_assisted_evidence_extraction` adds:

- `assisted_evidence_extraction_requests`
- `evidence_candidate_proposals`
- `assisted_extraction_request_status`
- `evidence_candidate_status`
- `evidence_candidate_acceptance_mode`

Migrations `0001` through `0007` were not modified.

## Extraction Architecture

`AssistedEvidenceExtractionService` owns the lifecycle:

```text
request -> provider candidates -> structural validation -> exact grounding
-> persisted candidates -> explicit accept/reject
```

Canonical Evidence is still created only through `ResearchService.register_evidence()`.

## Candidate Schema

Candidates include a candidate key, source content segment id, exact excerpt, offsets, proposed evidence type, relevance explanation, task-support flag, temporal applicability note, provider warnings, and extraction method version.

Extra provider fields are forbidden.

## Exact-Grounding Invariant

Darwin validates:

```text
segment.text[start_offset:end_offset] == exact_excerpt
```

Candidates that fail are persisted as `REJECTED_INVALID_GROUNDING`. Acceptance revalidates the same invariant before Evidence creation.

## Provider Design

The core protocol is:

```text
EvidenceExtractionProvider.propose_candidates(request, segments, limits)
```

The deterministic fake provider supports success, timeout, provider error, and malformed structured output simulation. The optional OpenAI adapter follows the Phase 1.9A environment/provider pattern and treats source content as untrusted data.

## Acceptance And Rejection

Acceptance requires `VALIDATED` status, reloads canonical segment content, revalidates provenance and grounding, checks duplicate accepted grounded spans, creates Evidence, creates an `EvidenceExtractionRecord`, links candidate to Evidence, and marks the candidate `ACCEPTED`.

Rejection requires a reason, preserves the candidate, and stores rejection timestamp/reason. Rejected candidates cannot be accepted by the default transition.

## Provenance

Assisted extraction records preserve ResearchRun, ResearchPlanItem, Source, Snapshot, Segment, provider/model/response id, method/prompt/schema versions, exact excerpt, offsets, validation results, grounding results, candidate state, and acceptance/rejection metadata.

Accepted Evidence metadata stores candidate id, request id, plan item id, snapshot id, segment id, and offsets.

## Security

Source content is untrusted data. It cannot grant tool, system, acquisition, shell, database, or policy-changing privileges. Provider credentials are environment-only and are not persisted.

## Tests And Results

Added deterministic tests for valid/invalid requests, provenance mismatches, fake provider behavior, provider failures, malformed output, exact grounding, invalid offsets, hallucinated excerpts, wrong segment references, duplicate keys, excessive candidates, candidate persistence, acceptance, revalidation, rollback, duplicate acceptance, rejection, prompt-injection-like source text, and no Claims/Conclusions/validation/synthesis/acquisition from proposals.

Verification results:

- full pytest: `124 passed`
- extraction-specific tests: `12 passed`
- planner regression tests: `10 passed`
- Phase 1.8 benchmark tests: `2 passed`
- acquisition/content/construction/synthesis/orchestration regression slice: `48 passed`
- CLI smoke: `darwin --help` and `darwin status` passed
- assisted extraction CLI smoke: `tests/test_cli.py::test_assisted_extraction_cli_propose_list_accept` passed as part of CLI tests
- Alembic offline upgrade head: passed
- Alembic offline downgrade `0008_assisted_evidence_extraction:0007_research_planning`: passed
- `git diff --check`: passed

## Docs

Created:

- `docs/method/assisted-evidence-extraction.md`
- `docs/runtime/assisted-evidence-extraction.md`

Updated:

- README
- docs index
- core data model docs

## ADRs

No ADR was added. Phase 1.9B extends the existing modular monolith and provider-agnostic boundaries without a new architectural decision.

## Limitations

Live provider extraction was not verified unless credentials are supplied in a later environment. The fake provider is the deterministic test authority. The OpenAI adapter is intentionally minimal.

## Deferred Work

Deferred:

- richer provider schema export
- live-provider benchmark
- candidate review UI
- bulk review
- extraction quality scoring
- automatic plan-item satisfaction
- autonomous downstream research

## Boundary Confirmation

No Phase 1.9C+ functionality was implemented.

Evidence proposal creates no Claims or Conclusions.

Evidence proposal does not validate Claims, synthesize research, launch acquisition, fetch content, or alter ResearchPlan completion state.

Manual Evidence extraction remains supported through the existing content service.

No autonomous acquisition or autonomous research loop was implemented.

No persistent files outside the Darwin repository were modified.
