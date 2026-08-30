# Assisted Claim Construction Method

Phase 1.9C introduces controlled assisted Claim construction. It helps draft atomic Claim candidates from canonical Evidence, but provider output remains a candidate proposal until explicitly accepted.

## Candidate vs Canonical Claim

A `ClaimCandidateProposal` is not a canonical `Claim`.

The boundary is:

```text
ResearchPlanItem + canonical Evidence -> Provider Claim Candidate Proposal
-> Structural Validation -> Persisted Candidate -> Explicit Acceptance
-> Canonical Claim + ClaimEvidence
```

Candidate creation never creates canonical Claims, ClaimEvidence links, validation evaluations, Conclusions, recommendations, confidence scores, Sources, Evidence, synthesis records, acquisition requests, or content fetches.

## Grounding Rule

Every candidate must cite Evidence ids supplied in the request. Provider prose, rationale, model knowledge, source URLs, and inferred background knowledge are not Evidence.

Darwin validates:

- each Evidence id exists
- each Evidence record belongs to the requested ResearchRun
- each Evidence record has source provenance
- each candidate Evidence id is inside the original request
- each candidate has at least one supporting, contradicting, or contextual Evidence link

Acceptance revalidates the same provenance before canonical Claim creation.

## Candidate Fields

Candidates include:

- candidate key
- proposed claim text
- proposed claim type
- supporting, contradicting, and contextual Evidence ids
- temporal scope when known
- qualifiers
- assumptions
- construction rationale
- provider warnings
- construction method version

The schema forbids extra fields, including arbitrary source URLs, canonical Claim ids, Conclusions, recommendations, validation states, confidence scores, or unsupported factual content without Evidence ids.

## Atomicity

Candidate text must be non-empty, within configured length limits, and structurally atomic. Darwin rejects list-like or multiline candidate text and recommendation language such as "should" or "recommend".

## Acceptance And Rejection

`accept_claim_candidate(candidate_id)` is explicit. It reloads the candidate, revalidates Evidence provenance, checks for a previously accepted duplicate with the same statement and Evidence-role set, creates a canonical Claim through `ResearchService.register_claim()`, creates ClaimEvidence links, writes a construction audit record, and marks the candidate accepted.

Duplicate acceptance of the same candidate is idempotent. Accepting another matching candidate fails clearly and does not create duplicate Claims.

`reject_claim_candidate(candidate_id, reason)` preserves the candidate, timestamp, and reason. Rejected candidates are not deleted and cannot be accepted by the default transition.

## Validation Boundary

Acceptance does not run `ClaimValidationService`. The accepted Claim remains `PROPOSED`, and structural validation remains absent until explicitly invoked by a later command or service call.

## Provider Boundary

Providers implement `ClaimConstructionProvider.propose_claims()`. Core Darwin remains provider agnostic.

Implemented providers:

- deterministic `FakeClaimConstructionProvider`
- optional minimal OpenAI adapter

Provider credentials are environment-only and are not persisted.

## Injection Defense

Evidence statements are treated as untrusted data. Text such as "Ignore previous instructions" inside Evidence has no tool, system, acquisition, shell, validation, or database authority. Provider prompts delimit Evidence as data and require Evidence ids back into canonical records.

## Limitations

Phase 1.9C does not implement automatic validation, confidence scoring, Conclusions, synthesis, recommendations, autonomous acquisition, recursive research loops, browser automation, embeddings, vector DB, graph DB, pgvector, multi-agent architecture, scheduled research, trading/exchange integration, bulk review UI, or live-provider quality benchmarking.
