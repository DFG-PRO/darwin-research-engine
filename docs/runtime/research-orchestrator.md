# Research Orchestrator

Phase 1.8E adds one deterministic orchestrator for the v0.1 modular monolith. Phase 1.8G leaves that orchestrator manual and additive: source content fetching and evidence extraction can occur before orchestration, but the orchestrator does not fetch content by itself.

## Responsibilities

`ResearchOrchestrator` coordinates:

- research run creation
- framing persistence
- plan item persistence
- supplied source and evidence intake
- explicit claim registration and claim/evidence linking
- claim validation through `ClaimValidationService`
- caller-supplied conclusion persistence
- deterministic synthesis
- completion assessment
- final lifecycle update when structurally complete

## Service Boundaries

The orchestrator uses `ResearchService` for persistence operations and `ClaimValidationService` for validation state, reason codes, and validation history.

The orchestrator owns method sequencing but does not duplicate persistence or validation rules already implemented in lower services.

`SourceContentService` is separate from the orchestrator. Evidence produced from explicit source-content extraction enters the existing workflow as normal persisted Evidence or caller-supplied evidence references.

## Transaction Behavior

`ResearchOrchestrator` accepts an explicit SQLAlchemy session. The caller owns the transaction boundary. CLI execution uses `session_scope`, which commits on success and rolls back on failure.

Service methods flush changes so database and structural errors surface before commit. Failed orchestration should leave no partially completed research record when run inside a transaction.

## Failure Behavior

The orchestrator fails explicitly when supplied input references unknown keys, duplicates local keys, or violates lower service rules.

Examples:

- evidence references an unknown source key
- evidence references an unknown plan item key
- a claim references an unknown evidence key
- human review references an unknown claim key

## Lifecycle Integration

The orchestrator creates a research run as `PENDING`, marks it `IN_PROGRESS`, and marks it `COMPLETED` only when completion assessment is `COMPLETE`.

Incomplete, contested, or human-review-required results remain `IN_PROGRESS`.

## Input Contract

`ManualResearchInput` accepts:

- research question
- optional public ID
- optional framing
- optional acquired source IDs
- plan items
- sources
- evidence
- claims and explicit evidence relationships
- conclusions
- explicit human-review claim keys

All source and evidence material must be supplied by the caller or explicitly registered before orchestration. The orchestrator does not autonomously discover, fetch, or extract material.

## Output Contract

`ResearchOrchestrationResult` returns:

- research run ID and public ID
- research question
- research method version
- run status
- framing summary
- plan completion
- source/evidence counts
- claim validation results
- unresolved contradictions
- evidence gaps
- assumptions
- conclusions
- warnings
- completion assessment
- synthesis record ID
- timestamps
