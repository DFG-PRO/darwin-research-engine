# Phase 1.9E Implementation Record

## Objective

Implement Darwin's first controlled end-to-end research loop: a bounded, observable, auditable, resumable where practical, synchronous controller that reuses existing Darwin research capabilities without bypassing their integrity boundaries.

## Baseline

Verified before modification:

- repository path: `/Volumes/BLACKBOX/2 CODE PROJECTS/Darwin Research Engine/darwin-research-engine`
- branch: `main`
- worktree clean before Phase 1.9E edits
- tags present: `phase-1.8`, `phase-1.9a`, `phase-1.9b`, `phase-1.9c`, `phase-1.9d`
- Phase 1.8 master and closure documentation exists
- Phase 1.9A, 1.9B, 1.9C, and 1.9D implementation records exist
- migration head before work: `0010_narrative_synthesis`
- planning, acquisition, content, extraction, claim assistance, validation, deterministic synthesis, narrative synthesis, and orchestration modules present
- baseline full pytest before modification: `149 passed`

## Scope

Implemented:

- dedicated `darwin.research_loop` module
- explicit loop request, budget, counter, event, and result schemas
- persistent loop execution, event, and query tables
- explicit execution modes: `MANUAL_GATE`, `AUTO_GROUNDED`, `DRY_RUN`
- explicit persisted state machine and stop reasons
- bounded acquisition query derivation from the approved plan item and research question
- hard budget checks for iterations, searches, sources, content, segments, candidates, acceptances, provider calls, runtime, tokens, and cost counters
- synchronous controller over existing planning, acquisition, content, assisted Evidence, assisted Claim, validation, structured synthesis, and narrative synthesis services
- manual-gate resume for Evidence approval, Claim approval, and synthesis publication
- auto-grounded acceptance through existing acceptance services with audited `AUTO_ACCEPTED` modes
- deterministic dry-run behavior with no canonical research records
- orchestration service helpers
- CLI commands for start, show, events, and resume
- migration `0011_research_loop`
- deterministic benchmark fixture and regression test
- method/runtime/data model documentation

## Files

Created:

- `src/darwin/research_loop/__init__.py`
- `src/darwin/research_loop/errors.py`
- `src/darwin/research_loop/schemas.py`
- `src/darwin/research_loop/service.py`
- `alembic/versions/0011_research_loop.py`
- `tests/test_research_loop.py`
- `tests/fixtures/phase_1_9e_loop_benchmark.json`
- `docs/method/controlled-research-loop.md`
- `docs/runtime/research-loop.md`
- `docs/benchmarks/phase-1.9e-controlled-research-loop-benchmark.md`
- `docs/implementation-record-phase-1.9e.md`

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
- `tests/test_cli.py`
- `tests/test_migrations.py`
- `tests/test_models.py`

## Schema And Migration

Migration `0011_research_loop` adds:

- `research_loop_executions`
- `research_loop_events`
- `research_loop_queries`
- `research_loop_execution_mode`
- `research_loop_state`
- `research_loop_stop_reason`

Migrations `0001` through `0010` were not modified.

## Controller Architecture

`ResearchLoopController` coordinates existing Darwin services:

```text
ResearchPlanner
-> AcquisitionService
-> SourceContentService
-> AssistedEvidenceExtractionService
-> AssistedClaimConstructionService
-> ClaimValidationService
-> StructuredSynthesisService
-> NarrativeSynthesisService
```

The loop persists orchestration state and events. It does not duplicate acquisition, content normalization, Evidence grounding, Claim provenance checks, validation, synthesis, or report publication logic.

## State Machine

States are explicit enums persisted on `ResearchLoopExecution`. Transition validation rejects unsupported transitions, and terminal states are terminal.

Waiting states are:

- `WAITING_EVIDENCE_APPROVAL`
- `WAITING_CLAIM_APPROVAL`
- `WAITING_SYNTHESIS_PUBLICATION`

Terminal states are:

- `COMPLETED`
- `STOPPED_NEEDS_EVIDENCE`
- `STOPPED_CONTRADICTION`
- `STOPPED_HUMAN_REVIEW`
- `STOPPED_BUDGET`
- `FAILED`

## Budgets

`ResearchLoopBudgets` defines request-level hard limits. `ResearchLoopController` validates those limits against system maxima from `Settings` before execution starts.

Consumed counters are stored on the execution and copied into events:

- iterations
- searches
- source candidates
- Sources registered
- content fetches
- segments processed
- Evidence proposals
- accepted Evidence
- Claim proposals
- accepted Claims
- provider calls
- tokens
- cost

The controller stops before a hard budget would be exceeded.

## Execution Modes

`MANUAL_GATE` stops at explicit operator approval points and returns a next required action.

`AUTO_GROUNDED` auto-accepts only validated candidates through existing acceptance services, with acceptance mode persisted as `AUTO_ACCEPTED`.

`DRY_RUN` validates control inputs and persists execution/events only. It does not create canonical Evidence or Claims and reports `INCOMPLETE`.

## Stop Conditions

Persisted stop reasons include success, waiting approvals, evidence gaps without budget, max iterations, unresolved contradiction, human review, provider failure, budget exhaustion, time budget exceeded, no usable sources, no canonical Evidence, no canonical Claims, fatal integrity error, and dry-run completion.

## Iteration Logic

The loop may perform another bounded acquisition/fetch/extraction cycle only when the completion assessment and remaining budgets permit it. It does not recurse indefinitely and does not automatically investigate contradictions or human-review states.

## Approval Flow

Planning is auto-approved inside the loop because acquisition requires an approved `ResearchRun` and plan. This approval is persisted on the planning proposal with `AUTO_APPROVED`.

Evidence and Claim approvals use the existing assisted acceptance services. Resume from manual gates does not duplicate canonical Evidence or Claims.

## Validation And Completion

Claim validation is performed by `ClaimValidationService`. Claim acceptance remains separate from validation.

Completion assessment is produced by `StructuredSynthesisService` and remains authoritative for loop decisions.

## Synthesis Handoff

Narrative synthesis runs only after canonical Claims have been validated and deterministic completion assessment permits synthesis. Publication remains controlled by the request mode and `publish_report` flag.

## Recovery

Supported recovery is explicit resume from waiting approval states. The execution record and append-only events make other stopped states inspectable even when they are not resumable in Phase 1.9E.

## Security

Research content and provider outputs are treated as untrusted data. Providers cannot choose arbitrary Darwin methods, shell commands, filesystem paths, database queries, network targets, or tools.

Secrets are not printed by the CLI and are not persisted in loop provider payloads.

## Deterministic Benchmark

Created a fake-provider end-to-end loop fixture:

- `tests/fixtures/phase_1_9e_loop_benchmark.json`
- `docs/benchmarks/phase-1.9e-controlled-research-loop-benchmark.md`

The fixture exercises question, plan, source acquisition, source registration, content fetch, snapshot/segment, Evidence proposal and auto-acceptance, Claim proposal and auto-acceptance, validation, completion assessment, narrative synthesis, and report publication.

Observed expected result in tests:

- state: `COMPLETED`
- stop reason: `SUCCESS_COMPLETE`
- completion assessment: `COMPLETE`
- iterations: 1
- queries: 1
- Sources: 1
- accepted Evidence: 1
- accepted Claims: 1
- validation distribution: `SUPPORTED: 1`

## Tests And Results

Verification results during implementation:

- baseline full pytest before modification: `149 passed`
- focused research loop/model/migration tests: `27 passed`
- research loop and CLI tests after adding fixture/CLI smoke: `21 passed`
- named regression slice covering research loop, 1.9A planner, 1.9B extraction, 1.9C Claim construction, 1.9D narrative synthesis, Phase 1.8I benchmark, acquisition, content, validation, orchestration, migrations, and CLI: `125 passed`
- full pytest after final changes: `162 passed`
- deterministic Phase 1.9E loop benchmark fixture: `1 passed`
- manual-gate resume smoke: `1 passed`
- CLI smoke: `darwin --help`, `darwin research --help`, `loop-start`, `loop-show`, and `loop-events` passed
- Alembic offline upgrade head compiled
- Alembic offline downgrade `0011_research_loop:0010_narrative_synthesis` compiled
- `git diff --check`: passed

## Live Smoke Status

No live external research smoke was run. Live credentials are not assumed, and live smoke absence is not blocking for Phase 1.9E.

## Documentation

Created:

- `docs/method/controlled-research-loop.md`
- `docs/runtime/research-loop.md`
- `docs/benchmarks/phase-1.9e-controlled-research-loop-benchmark.md`

Updated:

- README
- docs index
- core data model docs
- `.env.example`

## ADRs

No new ADR was added. Phase 1.9E follows the existing modular monolith and "no separate vector DB or graph DB" architecture decisions.

## Limitations

- Resume is limited to manual waiting gates.
- Live provider behavior is not benchmarked without credentials.
- Query derivation is simple and transparent.
- Semantic truth assessment remains outside deterministic validation.
- No UI exists for loop management.

## Deferred Work

Deferred:

- controlled contradiction-investigation mode
- richer resume/recovery from interrupted non-waiting stages
- live-provider benchmarks
- operator UI
- richer budget accounting for live token/cost usage
- report review/version workflow
- recommendation layer

## Boundary Confirmation

No unbounded autonomous loop, background research, recommendation engine, financial advice, trading/exchange integration, browser automation, vector database, graph database, embeddings, queue, daemon, scheduler, web UI, or Phase 1.9F+ functionality was implemented.

No commit, push, or tag was performed.
