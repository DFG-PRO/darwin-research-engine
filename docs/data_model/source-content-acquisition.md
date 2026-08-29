# Source Content Acquisition Data Model

Phase 1.8G adds content snapshot, segment, and evidence extraction audit records.

## SourceContentSnapshot

Table: `source_content_snapshots`

Represents one explicit fetch attempt for a registered Source.

Core fields:

- `id`: UUID primary key.
- `research_run_id`: required link to `research_runs`.
- `source_id`: required link to `sources`.
- `requested_locator`: locator Darwin attempted to fetch.
- `final_locator`: final locator after redirects, when known.
- `fetch_status`: explicit source fetch state.
- `fetched_at`: fetch timestamp.
- `content_type`: response content type when known.
- `response_status`: HTTP response status when available.
- `raw_content_fingerprint`: SHA-256 fingerprint for raw content.
- `normalized_content_fingerprint`: SHA-256 fingerprint for normalized text.
- `retrieval_method_version`: fetch method version.
- `normalization_method_version`: normalization method version.
- `raw_body_size`, `normalized_body_size`: content sizes.
- `raw_artifact_path`, `normalized_artifact_path`: artifact references under `DARWIN_ARTIFACT_ROOT`.
- `segment_count`: number of persisted segments.
- `warnings`, `errors`: explicit status details.
- `response_metadata`: sanitized response metadata.
- `metadata`: sanitized request metadata.

Snapshots are append-friendly and are not overwritten by later fetches.

## SourceContentSegment

Table: `source_content_segments`

Represents one deterministic segment of normalized source content.

Core fields:

- `id`: UUID primary key.
- `snapshot_id`: required link to `source_content_snapshots`.
- `source_id`: required link to `sources`.
- `segment_identifier`: stable identifier within the snapshot.
- `segment_order`: deterministic segment order.
- `text`: exact normalized segment text.
- `locator`: segment locator.
- `char_start`, `char_end`: offsets in the normalized snapshot text.
- `line_start`, `line_end`: line offsets in the normalized snapshot text.
- `fingerprint`: SHA-256 fingerprint for exact segment text.

## EvidenceExtractionRecord

Table: `evidence_extraction_records`

Represents one explicit extraction attempt from a source content segment.

Core fields:

- `id`: UUID primary key.
- `research_run_id`: required link to `research_runs`.
- `source_id`: required link to `sources`.
- `snapshot_id`: required link to `source_content_snapshots`.
- `segment_id`: required link to `source_content_segments`.
- `evidence_id`: linked Evidence when extraction succeeds.
- `extraction_status`: `EXTRACTED` or `FAILED`.
- `extraction_method_version`: extraction method version.
- `selected_text`: exact selected text.
- `selected_text_fingerprint`: SHA-256 fingerprint for the exact selected text.
- `selection_locator`: segment locator plus selected span.
- `char_start`, `char_end`: absolute offsets in normalized snapshot text.
- `warnings`, `errors`: explicit status details.
- `metadata`: sanitized extraction metadata.

## Status Values

`source_fetch_status` values:

- `SUCCESS`
- `FAILED`
- `UNSUPPORTED_CONTENT_TYPE`
- `TOO_LARGE`
- `ACCESS_DENIED`

`evidence_extraction_status` values:

- `EXTRACTED`
- `FAILED`

## Boundary

The model supports:

```text
Source -> SourceContentSnapshot -> SourceContentSegment -> EvidenceExtractionRecord -> Evidence
```

It does not create Claims, Conclusions, confidence scores, or semantic validations.
