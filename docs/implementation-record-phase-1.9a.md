# Phase 1.9A Implementation Record

## Objective

Implement Darwin's first controlled Research Task Planner. The planner turns an explicit research question plus optional framing constraints into a structured, auditable ResearchPlanProposal suitable for later acquisition and research execution.

## Scope

Implemented:

- provider-agnostic `ResearchPlanner`
- strict Pydantic planning request and proposal contracts
- deterministic fake planning provider
- minimal optional OpenAI planning provider adapter
- proposal persistence and proposal item persistence
- explicit approval flow into Phase 1.8 `ResearchRun`, `ResearchFraming`, and `ResearchPlanItem`
- orchestrator helper methods
- CLI planning commands
- Alembic migration
- deterministic tests and documentation

Not implemented:

- autonomous acquisition after planning
- recursive query generation
- autonomous research loops
- automatic Evidence extraction
- automatic Claim construction
- narrative synthesis
- recommendations
- contradiction detection beyond existing structural validation
- confidence scoring
- embeddings, vector DB, graph DB, or pgvector
- multi-agent architecture
- financial adapters or exchange APIs
- scheduled/background research
- UI

## Files Changed

Created:

- `src/darwin/planning/__init__.py`
- `src/darwin/planning/errors.py`
- `src/darwin/planning/providers.py`
- `src/darwin/planning/schemas.py`
- `src/darwin/planning/service.py`
- `alembic/versions/0007_research_planning.py`
- `tests/test_research_planner.py`
- `docs/method/research-planning.md`
- `docs/runtime/research-planner.md`
- `docs/implementation-record-phase-1.9a.md`

Modified:

- `src/darwin/db/models.py`
- `src/darwin/config/settings.py`
- `src/darwin/orchestration/service.py`
- `src/darwin/cli/app.py`
- `tests/test_cli.py`
- `tests/test_migrations.py`
- `docs/data_model/core-research-data-model.md`
- `README.md`
- `docs/README.md`

## Schema And Migration

Migration `0007_research_planning` adds:

- `research_plan_proposals`
- `research_plan_proposal_items`
- `research_plan_proposal_status`
- `research_plan_approval_mode`

It does not modify historical Phase 1.8 migrations.

## Planner And Provider Architecture

`ResearchPlanner` owns the planning workflow. Providers implement a protocol:

```text
generate_plan(request, limits) -> PlanningProviderResult
```

Core Darwin uses the protocol rather than depending directly on an LLM vendor.

## Structured Output Contract

Providers must return `ProviderPlanProposal`, including:

- normalized research question
- objective and scope
- exclusions and assumptions
- research categories
- bounded plan items
- expected evidence types
- suggested source types
- completion criteria
- warnings
- method, prompt, schema, and provenance metadata

Malformed or incomplete output is rejected.

## Approval Flow

Planning creates a `PROPOSED` proposal only. `approve_plan()` converts the proposal into:

- `ResearchRun`
- `ResearchFraming`
- pending `ResearchPlanItem` records

Approval mode is persisted as `MANUAL` or `AUTO_APPROVED`. Automatic approval exists only through explicit `auto_approve=True`.

## Safety Boundaries

The planner cannot create Sources, Evidence, Claims, Conclusions, acquisition requests, content snapshots, claim construction records, or synthesis records. It cannot launch acquisition or execute research.

Provider output is a planning proposal only. It is not evidence, not a claim, not a conclusion, and not knowledge.

Provider credentials are read from environment only and are not persisted.

## Tests

Deterministic coverage includes:

- valid and invalid planning request input
- valid fake provider proposal
- malformed provider output rejection
- duplicate task key rejection
- zero required task rejection
- excessive task count rejection
- provider timeout/error simulation
- proposal provenance persistence
- explicit and auto approval audit
- rollback of failed approval
- no Sources/Evidence/Claims/Conclusions/acquisition from planning
- CLI plan/show/approve smoke
- migration head and offline SQL checks

## Docs

Created:

- `docs/method/research-planning.md`
- `docs/runtime/research-planner.md`

Updated:

- `docs/data_model/core-research-data-model.md`
- `README.md`
- `docs/README.md`

## ADRs

No ADR was added. The implementation extends the existing provider-agnostic and modular-monolith architecture without introducing a new architectural decision.

## Limitations

The OpenAI adapter is implemented as a minimal optional HTTP provider contract. No live provider smoke was run during implementation because credentials were not assumed available and deterministic tests must remain the authority for this phase.

The planner suggests bounded tasks only. It does not generate recursive searches or execute downstream research.

## Deferred Work

Deferred to later phases:

- live planning provider verification in a credentialed environment
- richer editing/rejection workflows
- planner evaluation benchmarks
- acquisition handoff from approved plan items
- evidence intake improvements

## Phase Boundary Confirmation

No Phase 1.9B+ functionality was implemented.

No Sources, Evidence, Claims, or Conclusions are generated by the planner.

No autonomous acquisition or autonomous research loop was implemented.

No persistent files outside the Darwin repository were modified.
