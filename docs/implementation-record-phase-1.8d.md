# Phase 1.8D Implementation Record

## Objective

Implement deterministic claim validation foundations that evaluate the structural evidentiary state of a claim without determining truth or generating numeric confidence.

## Implemented Scope

- Added explicit source lineage fields.
- Added persisted claim validation evaluation history.
- Added explicit human review/validation event persistence.
- Added deterministic claim validation service.
- Added minimal validation CLI smoke command.
- Added deterministic tests for validation states, source independence, history, method versioning, and rollback behavior.
- Updated method, data model, runtime, README, and ADR documentation.

## Files Changed

- `src/darwin/db/models.py`
- `src/darwin/db/__init__.py`
- `src/darwin/research/service.py`
- `src/darwin/validation/__init__.py`
- `src/darwin/validation/errors.py`
- `src/darwin/validation/schemas.py`
- `src/darwin/validation/service.py`
- `src/darwin/cli/app.py`
- `alembic/versions/0002_claim_validation_foundation.py`
- `tests/test_claim_validation_service.py`
- `tests/test_cli.py`
- `tests/test_migrations.py`
- `tests/test_models.py`
- `README.md`
- `docs/README.md`
- `docs/data_model/core-research-data-model.md`
- `docs/runtime/research-run-lifecycle.md`
- `docs/method/claim-validation.md`
- `docs/decisions/ADR-006-claim-validation-history-and-source-lineage.md`
- `docs/implementation-record-phase-1.8d.md`

## Schema Changes

Added to `sources`:

- `origin_source_id`
- `source_lineage_type`

Added tables:

- `claim_validation_evaluations`
- `claim_human_validations`

Added enum types:

- `source_lineage_type`
- `claim_validation_state`
- `human_validation_type`

## Migration

Created Alembic revision:

- `0002_claim_validation_foundation`

The migration includes upgrade and downgrade paths.

## Validation Rules

- No evidence produces `INSUFFICIENT_EVIDENCE`.
- One supporting source produces `SUPPORTED`.
- Two independent supporting source origins produce `CORROBORATED`.
- Derived or republished sources with the same origin are not double-counted as independent corroboration.
- Support plus contradiction produces `CONTESTED`.
- Contradiction without support produces `CONTRADICTED`.
- Contextual evidence alone remains `INSUFFICIENT_EVIDENCE`.
- Explicit human review request produces `HUMAN_REVIEW_PENDING`.
- Explicit human validation produces `HUMAN_VALIDATED`.

## Tests

Added tests for:

- no evidence
- single support
- independent corroboration
- derived sources
- contradiction
- only contradiction
- contextual evidence
- human review
- human validation and auditable history
- method version persistence
- validation rollback behavior
- model metadata and Alembic migration regression
- CLI help regression

## Documentation

Created or updated:

- claim validation method documentation
- source-lineage and validation-history ADR
- data model documentation
- runtime lifecycle documentation
- README current status
- Phase 1.8D implementation record

## Deviations

No intentional deviations from Phase 1.8D scope.

## Known Limitations

- No automatic source-lineage discovery.
- No semantic evidence classification.
- No semantic contradiction detection.
- No source reputation scoring.
- No numeric or probabilistic confidence scoring.
- No live PostgreSQL migration was executed.
- Human validation is represented as explicit events only; no workflow, assignment, RBAC, or UI exists.

## Deferred Functionality

Deferred to later phases:

- source fetching
- web browsing
- external APIs
- AI/LLM calls
- framing and planning
- automated extraction
- automated claim generation
- validation methodology beyond deterministic structure
- confidence scoring
- synthesis and recommendations
- memory retrieval
- embeddings, pgvector, vector DB, graph DB
- multi-agent systems
- scheduled/background research
- financial/exchange adapters
- Arbitrage Engine integration
- UI

## Phase Boundary Confirmation

No Phase 1.8E+ functionality was implemented.
