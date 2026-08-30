# Assisted Evidence Extraction Method

Phase 1.9B introduces controlled assisted evidence extraction. It helps identify exact passages from stored source content, but provider output remains a candidate proposal until explicitly accepted.

## Candidate vs Canonical Evidence

An `EvidenceCandidateProposal` is not canonical `Evidence`.

The boundary is:

```text
ResearchPlanItem + SourceContentSegment -> Provider Candidate Proposal
-> Structural Validation -> Grounding Validation -> Persisted Candidate
-> Explicit Acceptance -> Canonical Evidence
```

Candidate creation never creates Claims, Conclusions, validation results, synthesis records, content fetches, or acquisition requests.

## Grounding Rule

Every candidate must reference a canonical `SourceContentSegment` and exact offsets. Darwin validates:

```text
segment.text[start_offset:end_offset] == exact_excerpt
```

If offsets exceed segment length or the excerpt differs from the stored segment text, the candidate is persisted as `REJECTED_INVALID_GROUNDING`. Darwin does not fuzzy-match or repair hallucinated quotations.

Acceptance reruns the same grounding check before canonical Evidence is created.

## Candidate Fields

Candidates include:

- candidate key
- source content segment id
- exact excerpt
- start and end offsets
- proposed evidence type
- relevance explanation
- research task support flag
- temporal applicability when known
- provider warnings
- extraction method version

The schema forbids extra fields, including arbitrary Evidence IDs, Claims, Conclusions, recommendations, or unsupported external citations.

## Acceptance And Rejection

`accept_candidate(candidate_id)` is explicit. It reloads the canonical segment, revalidates provenance and grounding, creates Evidence through `ResearchService.register_evidence()`, writes a manual-style `EvidenceExtractionRecord`, and links the candidate to the Evidence.

`reject_candidate(candidate_id, reason)` preserves the candidate, timestamp, and reason. Rejected candidates are not deleted and cannot be accepted by default.

Duplicate acceptance of the same candidate is idempotent. Accepting another candidate with the same run/source/snapshot/segment/offset/excerpt after one has already been accepted fails clearly and does not create duplicate Evidence.

## Provenance

Candidate records preserve:

- research run
- research plan item
- source
- snapshot
- segment
- provider and model
- provider response id
- method, prompt, and schema versions
- exact excerpt and offsets
- validation and grounding results
- candidate status
- acceptance or rejection metadata

Canonical Evidence created from an accepted candidate stores candidate id, request id, plan item id, snapshot id, segment id, and offsets in Evidence metadata.

## Temporal Metadata

The provider may propose temporal applicability as text. Darwin preserves source publication/retrieval/snapshot timestamps from canonical records and does not let the provider invent source dates. Unknown values remain unknown.

## Provider Boundary

Providers implement `EvidenceExtractionProvider.propose_candidates()`. Core Darwin remains provider agnostic.

Implemented providers:

- deterministic `FakeEvidenceExtractionProvider`
- optional minimal OpenAI adapter

Provider credentials are environment-only and are not persisted.

## Injection Defense

Source content is treated as untrusted data. Text such as "Ignore previous instructions" inside a segment has no tool, system, acquisition, shell, or database authority. Provider prompts delimit source content and require exact offsets back into stored text.

## Limitations

Phase 1.9B does not implement automatic Claim construction, Claim validation from provider output, Conclusions, synthesis, recommendations, autonomous acquisition, recursive research loops, browser automation, PDF/OCR/media extraction, embeddings, vector DB, graph DB, pgvector, multi-agent architecture, scheduled research, trading/exchange integration, or UI.
