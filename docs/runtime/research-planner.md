# Research Planner Runtime

Phase 1.9A adds `darwin.planning` as an additive runtime boundary.

## Provider Abstraction

Planning providers implement:

```text
PlanningProvider.generate_plan(request, limits) -> PlanningProviderResult
```

Core Darwin depends on this provider-agnostic protocol, not on a specific LLM vendor.

Implemented providers:

- `FakePlanningProvider`: deterministic, network-free, used by tests and local smoke checks.
- `OpenAIPlanningProvider`: minimal optional HTTP adapter using environment credentials.

The fake provider can simulate success, provider error, timeout, and invalid structured response.

## Request Flow

`ResearchPlanner.plan_research(request)`:

1. Builds configured planning limits.
2. Calls the selected provider.
3. Validates provider output as `ProviderPlanProposal`.
4. Applies deterministic structural checks.
5. Persists `research_plan_proposals` and `research_plan_proposal_items`.
6. Returns a proposal summary.

No `ResearchRun`, `Source`, `Evidence`, `Claim`, `Conclusion`, acquisition request, content fetch, construction record, or synthesis record is created by planning alone.

## Approval Flow

`ResearchPlanner.approve_plan(proposal_id)`:

1. Loads a `PROPOSED` proposal.
2. Revalidates the stored proposal payload.
3. Creates a `ResearchRun`.
4. Creates one `ResearchFraming`.
5. Creates pending `ResearchPlanItem` rows.
6. Marks the proposal `APPROVED`.
7. Stores approval mode, approval timestamp, and linked `ResearchRun` id.

The approval mode is `MANUAL` unless the caller explicitly used `auto_approve=True`, which records `AUTO_APPROVED`.

## Errors

Planner errors are represented by:

- `PlanningProviderError`
- `PlanningProviderTimeout`
- `PlanningConfigurationError`
- `PlanningValidationError`
- `PlanningApprovalError`

Provider failure, timeout, invalid structured output, and proposal validation failure never create partial research runs.

## Transaction Behavior

Services flush but do not commit. Callers own commit boundaries, matching the Phase 1.8 service style.

Approval uses a nested transaction around the creation of the run, framing, and plan items. If any insert or validation fails, the nested transaction rolls back and leaves the proposal in `PROPOSED` state.

## Orchestrator Integration

`ResearchOrchestrator` exposes additive methods:

```text
plan_research(request, provider=None, auto_approve=False)
approve_plan(proposal_id)
```

The existing manual workflow remains unchanged.

## CLI

Planning commands:

```bash
darwin research plan "Research question" --provider fake
darwin research plan "Research question" --auto-approve
darwin research plan-show <proposal-id>
darwin research plan-approve <proposal-id>
```

CLI output shows proposal id, provider/model, method, objective, categories, tasks, warnings, errors, approval status, and linked research run when approved.

The CLI does not print secrets or raw provider authentication data.

## Security

Provider credentials are read from environment variables only. The planner has no shell access, arbitrary database query access, acquisition capability, content fetch capability, or autonomous execution loop.

User-provided questions are provider input, not executable instructions. Provider output must match the schema and pass structural checks before persistence as a valid proposal.
