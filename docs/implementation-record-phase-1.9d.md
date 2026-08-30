# Phase 1.9D Implementation Record

## Objective

Implement Darwin's controlled assisted narrative research synthesis layer. The layer turns canonical Darwin research state into grounded structured narrative proposals, then requires explicit publication before a user-readable Markdown report artifact is created.

## Baseline

Verified before modification:

- repository path: `/Volumes/BLACKBOX/2 CODE PROJECTS/Darwin Research Engine/darwin-research-engine`
- branch: `main`
- clean worktree before Phase 1.9D edits
- tags present: `phase-1.8`, `phase-1.9a`, `phase-1.9b`, `phase-1.9c`
- Phase 1.8 master documentation exists
- Phase 1.9A, 1.9B, and 1.9C implementation records exist
- migration head before work: `0009_assisted_claim_construction`
- baseline tests: `137 passed`

## Scope

Implemented:

- dedicated `darwin.narrative_synthesis` module
- deterministic bounded `SynthesisContext` builder
- strict narrative synthesis request schema
- strict structured `NarrativeProposal` and `NarrativeFinding` schemas
- provider-agnostic `NarrativeSynthesisProvider` protocol
- deterministic fake provider
- minimal optional OpenAI adapter
- append-only request, proposal, finding, and report artifact persistence
- deterministic grounding/citation validation
- validation-state, contradiction, evidence-gap, and completion-assessment fidelity checks
- explicit proposal rejection
- explicit proposal publication to deterministic Markdown
- atomic report artifact writes under `DARWIN_ARTIFACT_ROOT`
- SHA-256 and artifact size persistence
- orchestrator helper methods
- CLI commands
- migration `0010_narrative_synthesis`
- deterministic tests and documentation

## Files

Created:

- `src/darwin/narrative_synthesis/__init__.py`
- `src/darwin/narrative_synthesis/errors.py`
- `src/darwin/narrative_synthesis/providers.py`
- `src/darwin/narrative_synthesis/schemas.py`
- `src/darwin/narrative_synthesis/service.py`
- `alembic/versions/0010_narrative_synthesis.py`
- `tests/test_narrative_synthesis.py`
- `docs/method/narrative-research-synthesis.md`
- `docs/runtime/narrative-research-synthesis.md`
- `docs/implementation-record-phase-1.9d.md`

Modified:

- `.env.example`
- `README.md`
- `docs/README.md`
- `docs/data_model/core-research-data-model.md`
- `src/darwin/cli/app.py`
- `src/darwin/config/settings.py`
- `src/darwin/db/__init__.py`
- `src/darwin/db/models.py`
- `src/darwin/orchestration/service.py`
- `tests/test_migrations.py`
- `tests/test_models.py`

## Schema And Migration

Migration `0010_narrative_synthesis` adds:

- `narrative_synthesis_requests`
- `narrative_synthesis_proposals`
- `narrative_synthesis_findings`
- `narrative_research_reports`
- `narrative_synthesis_request_status`
- `narrative_synthesis_proposal_status`

Migrations `0001` through `0009` were not modified.

## Source-Of-Truth Boundary

Narrative synthesis is downstream:

```text
Source / Snapshot / Segment
-> Evidence
-> Claim
-> Claim Validation
-> Conclusion
-> Narrative Synthesis
```

The narrative layer does not create or mutate Evidence, Claim text, ClaimEvidence, validation state, Conclusions, ResearchPlan records, Sources, acquisition, content snapshots, or recommendations.

## Context Builder

`NarrativeSynthesisService.build_context()` constructs a bounded provider-safe context from one `ResearchRun`. It includes framing, plan items, canonical Claims, latest validation states, Evidence and Source provenance, canonical Conclusions, evidence gaps, unresolved contradictions, human-review states, completion assessment, latest deterministic synthesis metadata, method version, schema version, and warnings.

Bounded selection prioritizes conclusion-linked Claims, corroborated Claims, contested/contradicted Claims, supported Claims, human-review Claims, and remaining Claims. Critical contested or contradicted Claims are not silently omitted; overflow fails explicitly.

## Provider Design

The provider protocol is:

```text
propose_synthesis(request, context, limits) -> ProviderNarrativeSynthesisResult
```

The deterministic fake provider supports success, timeout, provider error, and malformed structured output simulation. The optional OpenAI adapter follows the existing Responses API pattern and treats all canonical research text as untrusted data.

## Grounding Validation

Darwin validates:

- every material finding has a Claim or Conclusion reference
- executive summary has canonical references
- referenced Claim IDs are in the bounded context
- referenced Conclusion IDs are in the bounded context
- referenced Evidence IDs are in the bounded context
- validation summaries preserve exact state labels
- required contradiction material appears in the contradiction section
- evidence gaps remain visible
- completion assessment is not changed by the provider
- material findings do not use recommendation language
- uncertain or contested states are not upgraded with certainty language

Provider prose, provider reasoning, and provider metadata are never Evidence.

## Publication

Proposal creation does not publish.

`publish_synthesis(proposal_id)` reloads the proposal, rebuilds canonical context, revalidates grounding and completion fidelity, renders deterministic Markdown, writes the artifact atomically under:

```text
research-reports/<research_run_id>/<report_id>/report.md
```

It persists artifact path, SHA-256, size, report version, timestamp, and links the report to the proposal and ResearchRun. Duplicate publication is idempotent when a published proposal already has a report record.

## Tests And Results

Added deterministic tests for context building, fake provider persistence, provider failure/timeout/malformed output, unknown Claim/Conclusion/Evidence references, validation-state fidelity, contradiction preservation, evidence-gap/completion fidelity, bounded selection, context overflow, explicit publication, duplicate publication, artifact checksum/path persistence, publication rollback behavior, proposal rejection, and canonical-state boundary preservation.

Verification results during implementation:

- baseline full pytest before modification: `137 passed`
- focused narrative/model/migration tests: `27 passed`
- full pytest after implementation: `149 passed`
- CLI smoke: `darwin --help` and `darwin research --help` passed
- `git diff --check`: passed
- optional ruff check not run because `ruff` is not installed in the project virtual environment

## Docs

Created:

- `docs/method/narrative-research-synthesis.md`
- `docs/runtime/narrative-research-synthesis.md`

Updated:

- README
- docs index
- core data model docs

## Limitations

Live provider narrative synthesis was not verified because credentials are not assumed. The fake provider is the deterministic test authority. Validation-state fidelity includes deterministic safeguards, but semantic fidelity cannot be fully solved with deterministic checks alone.

## Deferred Work

Deferred:

- richer provider schema export
- live-provider benchmark
- report review UI
- editable proposal workflow
- report versioning beyond initial one-report-per-proposal publication
- recursive/map-reduce narrative synthesis
- recommendation layer
- PDF/DOCX report generation

## Boundary Confirmation

No recommendation engine was implemented.

Narrative synthesis creates no Evidence, no canonical Claims, no ClaimEvidence, no validation evaluations, no canonical Conclusions, no Sources, no content snapshots, no acquisition requests, and no autonomous research loop.

No commit, push, or tag was performed.
