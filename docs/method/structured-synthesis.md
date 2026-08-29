# Structured Synthesis Method

Phase 1.8H adds deterministic structured synthesis over persisted research records.

## Purpose

Structured synthesis preserves the chain:

```text
Source -> Snapshot -> Segment -> Evidence -> Claim -> Validation -> Synthesis -> Conclusion
```

Snapshot and Segment are present when evidence came from explicit source-content extraction. Evidence that was supplied directly still retains Source provenance.

## Behavior

`StructuredSynthesisService` loads a ResearchRun and emits an append-only `ResearchSynthesisRecord` containing:

- research question and method version
- synthesis method version
- source, evidence, claim, and conclusion counts
- claim views with evidence/source/snapshot/segment provenance
- validation state and reason codes
- explicit conclusion-to-claim relationships
- evidence gaps
- unresolved contradictions
- deterministic warnings
- completion assessment

The service does not generate conclusions, recommendations, claim statements, or new evidence.

## Warning Rules

Synthesis warns when claims or conclusion dependencies are:

- insufficiently evidenced
- contested
- contradicted
- pending human review
- human validated

Human validation is preserved as a distinct validation state. It is not counted as an independent source.

## History

Each synthesis call creates a new `ResearchSynthesisRecord`. Older records are preserved.

## Boundary

Not implemented in Phase 1.8H:

- narrative report generation
- recommendation synthesis
- confidence scoring
- semantic claim clustering
- contradiction resolution
- retrieval over historical memory
