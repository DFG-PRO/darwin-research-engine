# Phase 1.8E Implementation Record

## Objective

Implement Darwin's first deterministic research method and orchestration layer over explicitly supplied research material.

## Scope

Implemented a manual supplied-material research workflow covering framing, planning, material intake, explicit claim registration, claim validation, deterministic synthesis, conclusion persistence, and completion assessment.

## Files Changed

- `src/darwin/db/models.py`
- `src/darwin/db/__init__.py`
- `src/darwin/orchestration/__init__.py`
- `src/darwin/orchestration/errors.py`
- `src/darwin/orchestration/schemas.py`
- `src/darwin/orchestration/service.py`
- `src/darwin/cli/app.py`
- `alembic/versions/0003_research_method_orchestration.py`
- `tests/conftest.py`
- `tests/fixtures/manual_research_complete.json`
- `tests/test_research_orchestrator.py`
- `tests/test_cli.py`
- `tests/test_migrations.py`
- `tests/test_models.py`
- `README.md`
- `docs/README.md`
- `docs/data_model/core-research-data-model.md`
- `docs/method/research-method-v0.1.md`
- `docs/runtime/research-orchestrator.md`
- `docs/decisions/ADR-007-deterministic-supplied-material-orchestration.md`
- `docs/implementation-record-phase-1.8e.md`

## Schema and Migrations

Created Alembic revision `0003_research_method_orchestration`.

Added tables:

- `research_framings`
- `research_plan_items`
- `research_synthesis_records`

Added enum types:

- `research_plan_item_status`
- `research_plan_priority`
- `research_completion_assessment`

## Research Method Stages

- Create research run.
- Persist framing.
- Persist plan items.
- Register supplied sources and evidence.
- Register explicit claims and claim/evidence relationships.
- Validate each claim structurally.
- Persist caller-supplied conclusions.
- Build deterministic synthesis.
- Assess completion.
- Mark research run completed only when structurally complete.

## Completion Rules

- Human review pending -> `HUMAN_REVIEW_REQUIRED`
- Contested claim -> `UNRESOLVED_CONTRADICTION`
- Required plan evidence missing -> `NEEDS_EVIDENCE`
- No claims -> `INCOMPLETE`
- Otherwise -> `COMPLETE`

## Verification Results

- Verified working directory with `pwd`.
- Inspected `git status`, current branch, tags, existing models, services, migrations, tests, documentation, and ADRs.
- Confirmed `phase-1.8d` tag exists.
- Ran `.venv/bin/python -m pytest`; all 52 tests passed.
- Ran `.venv/bin/darwin --help`; CLI loaded.
- Ran `.venv/bin/darwin status`; existing status command returned ok.
- Ran `.venv/bin/darwin research --help`; research command group loaded.
- Ran `.venv/bin/darwin research run-manual --help`; manual research command loaded.
- Ran `darwin research run-manual` against `tests/fixtures/manual_research_complete.json` using a temporary local SQLite database; command returned a structured `COMPLETE` result.
- Ran `.venv/bin/alembic upgrade head --sql`; Alembic generated offline SQL through revision `0003_research_method_orchestration`.
- Ran `.venv/bin/alembic downgrade 0003_research_method_orchestration:0002_claim_validation_foundation --sql`; Alembic generated downgrade SQL for the new revision.
- Ran `git diff --check`.
- Reviewed `git diff --stat`, `git diff --name-status`, and `git status --short`.

## Limitations

- Orchestration accepts supplied material only.
- Plan satisfaction is based on explicit evidence-to-plan item keys.
- Conclusions are caller-supplied.
- No live PostgreSQL migration was executed.
- CLI manual execution requires a configured database with migrations applied.

## Deferred Functionality

Deferred:

- web browsing and web search
- URL fetching and scraping
- external research, financial, exchange, or market-data APIs
- LLM calls
- AI-generated framing, plans, evidence, claims, or synthesis
- semantic contradiction detection
- source reputation scoring
- numeric confidence scoring
- recommendation engine
- autonomous or scheduled research
- memory retrieval
- embeddings, pgvector, vector DB, graph DB
- multi-agent architecture
- Arbitrage Engine integration
- web UI

## Phase Boundary Confirmation

No Phase 1.8F+ functionality was implemented.
