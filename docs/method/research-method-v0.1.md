# Research Method v0.1

Phase 1.8E introduced Darwin's first deterministic end-to-end research method over supplied material. Phase 1.8F added controlled external source discovery as an optional pre-evidence acquisition step. Phase 1.8G adds explicit source content fetching, snapshotting, segmentation, and exact evidence extraction. Phase 1.8H adds caller-supplied evidence-to-claim construction and structured synthesis records. The method still does not crawl, call LLMs, infer claims, classify evidence semantically, or generate recommendations.

## Purpose

The method coordinates a complete auditable research workflow:

1. Research question
2. Framing
3. Research plan
4. Optional external source discovery
5. Optional explicit source content fetch
6. Optional explicit segment/span evidence extraction
7. Supplied source and evidence intake
8. Explicit claim construction or legacy explicit claim registration
9. Structural claim validation
10. Caller-supplied conclusions and explicit conclusion-to-claim links
11. Deterministic structured synthesis
12. Completion assessment

## Framing

Framing records are persisted in `research_framings`. They preserve the original question, normalized question, objective, scope, exclusions, decision criteria, assumptions, required evidence categories, and completion criteria.

The orchestrator applies only simple deterministic defaults when fields are omitted.

## Planning

Plan items are persisted in `research_plan_items`. Each plan item records requirement, category, priority, required/optional status, lifecycle status, optional expected source type, and notes.

Plan item status is updated only from supplied evidence references. Darwin does not infer that a plan item is satisfied from prose.

## Material Intake

Evidence material must be supplied by the caller. Each evidence item references a supplied source key and may reference plan item keys. Material intake uses `ResearchService` so provenance rules remain centralized.

## External Source Discovery

External acquisition enters before evidence intake. A caller may submit an explicit acquisition request for an existing research run. Darwin records the provider, query, constraints, returned source candidates, warnings/errors, and source registration outcomes.

Accepted source candidates are registered as `Source` records through `ResearchService`. They may be supplied back to the manual orchestrator as `acquired_source_ids`.

Discovered sources do not automatically satisfy plan items. Provider snippets are not Evidence. Source candidates are not Claims. Any later evidence capture must be explicit and traceable to a Source.

## Source Content and Evidence Extraction

Registered Sources may be fetched explicitly. Darwin persists a content snapshot, writes raw and normalized artifacts under `DARWIN_ARTIFACT_ROOT`, normalizes supported HTML/text content, and creates deterministic source segments.

Evidence extraction is caller-selected. A full segment or exact character span can become an `EXCERPT` Evidence record through `ResearchService`. The extraction record preserves Source, Snapshot, Segment, selection locator, offsets, fingerprint, and extraction method version.

Fetching a Source does not automatically create Evidence. Extracting Evidence does not create Claims or run validation automatically.

## Claim Construction

Claims are explicit caller inputs. Evidence relationships are explicit and use existing claim/evidence relationship semantics such as `SUPPORTS`, `CONTRADICTS`, and `CONTEXTUALIZES`.

When claims cite evidence, Phase 1.8H routes them through `ClaimConstructionService`. The caller must provide the claim statement, claim type, selected evidence IDs, evidence relationships, and construction metadata. Darwin persists the Claim, claim/evidence links, a `ClaimConstructionRecord`, and selected construction evidence rows.

Darwin does not generate claims from evidence in Phase 1.8H.

## Validation

The orchestrator invokes `ClaimValidationService` for each supplied claim. Validation states and reason codes are included in the final result and persisted through validation history.

## Synthesis

Synthesis is deterministic and structural. It assembles research question, method version, source/evidence counts, claim validation states, evidence/source/snapshot/segment provenance, explicit conclusion-to-claim dependencies, unresolved contradictions, evidence gaps, warnings, and completion assessment.

Synthesis does not invent conclusions, claim statements, recommendations, or unsupported prose.

## Completion Rules

Completion assessment is deterministic:

- `HUMAN_REVIEW_REQUIRED` if any claim is in human review pending state.
- `UNRESOLVED_CONTRADICTION` if any claim is contested.
- `NEEDS_EVIDENCE` if required plan items remain pending.
- `INCOMPLETE` if there are no claims.
- `COMPLETE` otherwise.

Only `COMPLETE` marks the research run completed. Other successful but incomplete assessments leave the run in progress.

## Method Versioning

The method version comes from `DARWIN_RESEARCH_METHOD_VERSION`. Each research run and synthesis record preserves the method version used.

## Auditability

Framing, plan items, validation evaluations, human validation events, synthesis records, acquisition requests, source candidates, content snapshots, source segments, evidence extraction records, claim construction records, and conclusion-to-claim links are persisted as auditable records. Darwin avoids storing the whole workflow only as one opaque JSON blob.

## Limitations

- No autonomous research.
- No general web crawling.
- No automatic content fetching from discovered Sources.
- No AI-generated framing, planning, evidence, claims, or synthesis.
- No semantic contradiction detection.
- No source quality scoring.
- No numeric confidence scoring.
- No recommendation generation.
- No memory retrieval, embeddings, pgvector, vector DB, graph DB, or multi-agent system.
