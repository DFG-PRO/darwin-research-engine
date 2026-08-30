# Narrative Research Synthesis Runtime

Phase 1.9D runtime flow:

```text
ResearchRun
-> deterministic SynthesisContext
-> NarrativeSynthesisProvider
-> structured NarrativeProposal
-> deterministic grounding validation
-> persisted proposal
-> explicit publish
-> Markdown report artifact
```

## Commands

```bash
darwin research propose-synthesis <run-id> --provider fake
darwin research synthesis-show <proposal-id>
darwin research publish-synthesis <proposal-id>
darwin research reject-synthesis <proposal-id> --reason "reason"
```

`propose-synthesis` creates an append-only provider proposal. It does not publish a report and does not mutate Evidence, Claims, ClaimEvidence, validation records, Conclusions, plans, or Sources.

`publish-synthesis` is explicit. It revalidates current canonical state before writing a deterministic Markdown report below `DARWIN_ARTIFACT_ROOT`.

## Providers

`fake` is deterministic and network-free.

`openai` is optional and uses the existing OpenAI API key setting. The adapter receives only the bounded synthesis context and asks for strict structured output.

## Failure Behavior

Invalid run context, missing canonical Claims, provider failure, timeout, malformed output, unknown references, omitted contradictions, omitted evidence gaps, completion mismatch, excessive findings, artifact write failure, and duplicate publication are handled without creating or modifying canonical research state.

Duplicate publication is idempotent when a proposal is already published and has a report record.
