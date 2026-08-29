# Research Method v0.1

Phase 1.8E introduced Darwin's first deterministic end-to-end research method over supplied material. Phase 1.8F adds controlled external source discovery as an optional pre-evidence acquisition step. The method still does not crawl, fetch full content, call LLMs, infer claims, classify evidence, or generate recommendations.

## Purpose

The method coordinates a complete auditable research workflow:

1. Research question
2. Framing
3. Research plan
4. Optional external source discovery
5. Supplied source and evidence intake
6. Explicit claim registration
7. Structural claim validation
8. Deterministic synthesis
9. Caller-supplied conclusions
10. Completion assessment

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

## Claim Registration

Claims are explicit caller inputs. Evidence relationships are explicit and use existing claim/evidence relationship semantics such as `SUPPORTS`, `CONTRADICTS`, and `CONTEXTUALIZES`.

Darwin does not generate claims from evidence in Phase 1.8E.

## Validation

The orchestrator invokes `ClaimValidationService` for each supplied claim. Validation states and reason codes are included in the final result and persisted through validation history.

## Synthesis

Synthesis is deterministic and structural. It assembles research question, objective, method version, run status, source/evidence counts, claim validation states, unresolved contradictions, evidence gaps, assumptions, caller-supplied conclusions, warnings, and completion assessment.

Synthesis does not invent conclusions or unsupported prose.

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

Framing, plan items, validation evaluations, human validation events, synthesis records, acquisition requests, and source candidates are persisted as auditable records. Darwin avoids storing the whole workflow only as one opaque JSON blob.

## Limitations

- No autonomous research.
- No general web crawling or content extraction.
- No AI-generated framing, planning, evidence, claims, or synthesis.
- No semantic contradiction detection.
- No source quality scoring.
- No numeric confidence scoring.
- No recommendation generation.
- No memory retrieval, embeddings, pgvector, vector DB, graph DB, or multi-agent system.
