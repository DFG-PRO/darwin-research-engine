# Evidence Extraction

Phase 1.8G introduces deterministic exact evidence extraction from fetched source content.

## Philosophy

Evidence must be exact, bounded, and traceable. Darwin does not decide what is important evidence in this phase. A caller must explicitly select a segment or span.

The provenance chain is:

```text
Source -> SourceContentSnapshot -> SourceContentSegment -> EvidenceExtractionRecord -> Evidence
```

## Extraction Rules

- Full segment extraction uses the segment text exactly.
- Span extraction uses explicit segment-relative character offsets.
- Extracted text is not paraphrased or rewritten.
- Evidence is registered as `EvidenceType.EXCERPT`.
- Evidence metadata records snapshot ID, segment ID, selection offsets, and extraction method version.
- The extraction audit record stores selected text, fingerprint, locator, offsets, status, warnings/errors, and method version.

## Excerpt Size Limit

`DARWIN_EVIDENCE_EXCERPT_MAX_CHARS` limits one evidence excerpt. Oversized selections produce a failed extraction record and do not create Evidence.

Full source content stays in artifacts and normalized segments; Evidence should remain a bounded excerpt.

## Method Versioning

The default extraction method version is `segment-extraction-1.8g`, configurable through `DARWIN_EVIDENCE_EXTRACTION_METHOD_VERSION`.

## Boundaries

Evidence extraction does not create Claims, run claim validation, infer conclusions, score confidence, or determine truth.

## Known Limitations

- Segmentation is paragraph-based.
- No semantic chunking.
- No embeddings.
- No AI extraction.
- No PDF/image/audio/video/office document extraction.
