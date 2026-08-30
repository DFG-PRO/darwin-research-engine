# Narrative Research Synthesis

Phase 1.9D adds Darwin's controlled assisted narrative synthesis layer.

Narrative synthesis is presentation, not knowledge creation.

The source-of-truth hierarchy remains:

```text
Source / Snapshot / Segment
-> Evidence
-> Claim
-> Claim Validation
-> Conclusion
-> Narrative Synthesis
```

The narrative layer is strictly downstream. It may organize, summarize, compare, and explain canonical Darwin state. It must not create Evidence, create canonical Claims, validate Claims, create canonical Conclusions, alter ResearchPlan records, fetch URLs, execute tools, or fill evidence gaps using provider memory.

## Controlled Context

The provider receives a deterministic bounded `SynthesisContext`, not arbitrary database access. The context contains the research question, latest framing, plan items, canonical Claims, latest validation states, ClaimEvidence relationships, Evidence excerpts and locators, Source metadata, canonical Conclusions, evidence gaps, unresolved contradictions, human-review states, completion assessment, and method/schema metadata.

If context bounds would omit critical contested or contradicted material, Darwin fails explicitly instead of silently hiding the conflict.

## Structured Proposal

Providers return a strict structured `NarrativeProposal`, not arbitrary Markdown. Material findings must reference canonical Claim and/or Conclusion IDs. Optional Evidence references must also be supplied IDs from the bounded context.

Darwin revalidates every provider reference. Unknown Claim IDs, wrong-run IDs, invented Conclusion IDs, and Evidence IDs outside context reject the proposal.

## Fidelity Rules

Validation state wording must not upgrade certainty:

- `UNASSESSED` remains unassessed.
- `INSUFFICIENT_EVIDENCE` remains uncertain.
- `SUPPORTED` can be described only as supported by available evidence.
- `CORROBORATED` can be described as independently corroborated.
- `CONTESTED` and `CONTRADICTED` must remain visible.
- `HUMAN_REVIEW_PENDING` remains pending.
- `HUMAN_VALIDATED` may be called human validated.

Deterministic checks enforce ID grounding, required contradiction visibility, evidence-gap visibility, completion-assessment fidelity, and basic certainty/recommendation boundary language. They do not claim to solve all semantic fidelity problems.

## Publication

Proposal creation does not publish a report.

`publish_synthesis(proposal_id)` reloads the proposal, rebuilds current canonical context, revalidates references and completion fidelity, renders deterministic Markdown, writes it atomically below `DARWIN_ARTIFACT_ROOT/research-reports/...`, stores SHA-256 and size metadata, and marks the proposal `PUBLISHED`.

Reports use Darwin references such as `[Claim: <id>]`, `[Evidence: <id>]`, and `[Source: <id>]`. They do not fabricate web-style citations.

## Recommendation Boundary

Phase 1.9D is not a recommendation engine. Reports may label future research questions, but must not produce financial advice, buy/sell actions, business decisions, execution instructions, or recommendations presented as research findings.
