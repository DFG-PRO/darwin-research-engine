# Research Planning Method

Phase 1.9A introduces Darwin's first controlled Research Task Planner. The planner transforms an explicit research question and optional framing constraints into a structured ResearchPlanProposal.

The planner does not execute research. Its output is a proposal for what to investigate next.

## Boundary

Planning follows this boundary:

```text
Research Question -> Planning Request -> Proposed Framing -> Proposed Plan
-> Structural Validation -> Persisted Proposal -> Explicit Approval
```

The following states are intentionally distinct:

- `PROPOSED PLAN`: generated and persisted for inspection.
- `APPROVED PLAN`: converted into a `ResearchRun`, `ResearchFraming`, and pending `ResearchPlanItem` records.
- `EXECUTED RESEARCH`: later source acquisition, evidence extraction, claim construction, and synthesis.

Phase 1.9A implements the first two states only. It does not launch acquisition or autonomous research.

## LLM Planning Boundary

An LLM provider may be used to suggest a plan. That output is not Evidence, not a Claim, not a Conclusion, and not Darwin knowledge. It is accepted only after strict Pydantic validation and deterministic structural checks.

Unsupported or invented factual statements in a provider proposal stay inside planning proposal text. They do not enter the evidence, claim, conclusion, acquisition, or synthesis layers.

## Structured Output

Planning providers must return a structured `ProviderPlanProposal` containing:

- normalized research question
- proposed objective and scope
- exclusions and assumptions
- research categories
- proposed plan items
- expected evidence types
- suggested source types
- completion criteria
- planner warnings
- method, prompt, schema, provider, and provenance metadata

Free-form prose parsing is not part of the core planner contract.

## Structural Validation

The planner applies deterministic checks before a proposal can be persisted as `PROPOSED`:

- at least one required task
- no duplicate task keys
- bounded total task count
- bounded required task count
- bounded category count
- explicit objective
- explicit scope
- non-empty categories
- non-empty task requirements
- explicit task completion criteria
- source-type requirements
- expected evidence type requirements
- no completed task status before execution
- no evidence IDs in provider output
- no conclusions in provider output

Malformed output is persisted as `FAILED` only when the caller's transaction allows it, and it never creates a `ResearchRun`.

## Provenance

Persisted proposals store:

- original planning request
- provider id and model
- provider response id when available
- planner method version
- prompt version
- schema version
- warnings and validation result
- proposal payload
- provider metadata
- usage and cost metadata when available
- approval status and approval mode
- linked `ResearchRun` id after approval

Secrets and authentication headers are not persisted.

## Versioning

Planning semantics are versioned through:

- `DARWIN_RESEARCH_PLANNING_METHOD_VERSION`
- `DARWIN_RESEARCH_PLANNING_PROMPT_VERSION`
- `DARWIN_RESEARCH_PLANNING_SCHEMA_VERSION`

Provider adapters must persist these values so future proposal history can be interpreted against the planning method that produced it.

## Approval Model

`ResearchPlanner.approve_plan()` converts a valid proposal into Phase 1.8-compatible records:

- `ResearchRun`
- `ResearchFraming`
- `ResearchPlanItem`

Approval is explicit. Automatic approval is allowed only through `auto_approve=True`, which records `AUTO_APPROVED` on the proposal. The default approval mode is `MANUAL`.

Approval runs in a nested transaction. If framing or plan item persistence fails, no partial `ResearchRun` remains.

## Limitations

Phase 1.9A does not implement recursive planning, query generation, autonomous acquisition, automatic Evidence extraction, Claim construction, synthesis, confidence scoring, recommendations, memory retrieval, vector storage, graph storage, scheduled research, UI, or domain adapters.
