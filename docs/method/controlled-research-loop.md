# Controlled Research Loop

Phase 1.9E adds Darwin's first bounded end-to-end research loop.

The loop is automation, not unbounded autonomy. It coordinates existing Darwin services in a fixed order and records every durable stage. It does not invent evidence, bypass candidate acceptance, replace claim validation, resolve contradictions by itself, or run background research.

## Method Boundary

The controlled loop follows this sequence:

```text
ResearchLoopRequest
-> Planning Proposal
-> Plan Approval
-> Acquisition
-> Source Registration
-> Content Fetch
-> Snapshot / Segment
-> Evidence Candidate Proposal
-> Evidence Acceptance Policy
-> Claim Candidate Proposal
-> Claim Acceptance Policy
-> Claim Validation
-> Completion Assessment
-> Optional Iteration
-> Narrative Synthesis Proposal
-> Optional Report Publication
-> ResearchLoopResult
```

Each arrow calls an existing subsystem. The loop owns control flow and budgets; the subsystems remain the authority for their own canonical records.

## Execution Modes

`MANUAL_GATE` stops at approval boundaries. Evidence candidates, Claim candidates, and report publication require explicit operator action before the loop resumes.

`AUTO_GROUNDED` can auto-accept only validated Evidence candidates and validated Claim candidates through the existing acceptance services. Evidence acceptance still revalidates exact grounding. Claim acceptance still requires canonical Evidence provenance. Accepted Claims remain subject to the existing validation service.

`DRY_RUN` validates the request, budget envelope, provider selection, event persistence, and shallow control path. It creates a loop execution and events only. It does not create a `ResearchRun`, Sources, Evidence, Claims, synthesis proposals, or reports, and it reports `INCOMPLETE`.

## State Machine

Loop states are explicit and persisted:

```text
PENDING
PLANNING
ACQUIRING
FETCHING_CONTENT
EXTRACTING_EVIDENCE
WAITING_EVIDENCE_APPROVAL
CONSTRUCTING_CLAIMS
WAITING_CLAIM_APPROVAL
VALIDATING
ASSESSING_COMPLETION
ITERATING
SYNTHESIZING
WAITING_SYNTHESIS_PUBLICATION
COMPLETED
STOPPED_NEEDS_EVIDENCE
STOPPED_CONTRADICTION
STOPPED_HUMAN_REVIEW
STOPPED_BUDGET
FAILED
```

Invalid transitions fail before state is mutated. Terminal states are terminal.

## Budgets

Every request carries hard limits for iterations, searches, source candidates/registrations, content fetches, processed segments, Evidence candidates, accepted Evidence, Claim candidates, accepted Claims, provider calls, runtime seconds, and optional token/cost counters.

Request limits must fit inside configured system maxima. The controller checks budgets before work that would consume them and stops with `STOPPED_BUDGET` instead of spending "one more" unit.

## Iteration Policy

The default iteration count is small. The loop can iterate only when completion is not final, iteration budget remains, search budget remains, and required plan work remains. It does not recursively search to resolve disagreement or satisfy vague curiosity.

`UNRESOLVED_CONTRADICTION`, `HUMAN_REVIEW_REQUIRED`, provider failure, and budget exhaustion stop the loop by default.

## Validation And Completion

The loop uses `ClaimValidationService` after canonical Claims exist. Provider output never sets validation state.

Completion is assessed by deterministic structured synthesis. The loop reacts to the assessment:

- `COMPLETE`: proceed to narrative synthesis.
- `NEEDS_EVIDENCE` or `INCOMPLETE`: iterate only if hard capacity remains; otherwise stop.
- `UNRESOLVED_CONTRADICTION`: stop.
- `HUMAN_REVIEW_REQUIRED`: stop.

## Approval Modes

Planning approval inside the loop is auto-approved and audited on the planning proposal because acquisition cannot begin until a `ResearchRun`, framing, and plan items exist.

Evidence and Claim acceptance obey the selected loop mode. Manual acceptance is done through existing candidate acceptance APIs or CLI commands, then `loop-resume` continues from the waiting state.

## Stop Conditions

Stop reasons include:

```text
SUCCESS_COMPLETE
NEEDS_EVIDENCE_NO_BUDGET
MAX_ITERATIONS_REACHED
UNRESOLVED_CONTRADICTION
HUMAN_REVIEW_REQUIRED
WAITING_EVIDENCE_APPROVAL
WAITING_CLAIM_APPROVAL
WAITING_SYNTHESIS_PUBLICATION
PROVIDER_FAILURE
BUDGET_EXHAUSTED
TIME_BUDGET_EXCEEDED
NO_USABLE_SOURCES
NO_CANONICAL_EVIDENCE
NO_CANONICAL_CLAIMS
FATAL_INTEGRITY_ERROR
DRY_RUN_COMPLETE
```

Waiting states are not success. They include a next required action in `ResearchLoopResult`.

## Contradiction And Human Review

Contradictions remain part of canonical validation and synthesis state. The loop does not search forever trying to eliminate them.

Human review remains explicit. If a Claim enters a human-review state and completion requires review, the loop stops with `STOPPED_HUMAN_REVIEW`.

## Limitations

Phase 1.9E is synchronous and explicitly invoked. It has no scheduler, queue, worker, browser automation, recommendation layer, vector database, graph database, embeddings, trading integration, or automatic contradiction investigation.
