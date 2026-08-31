# Research Loop Runtime

Phase 1.9E runtime flow is synchronous and invocation-bound:

```text
darwin research loop-start
-> ResearchLoopController.start()
-> existing Darwin services
-> persisted ResearchLoopExecution / ResearchLoopEvent
-> ResearchLoopResult
```

There are no background workers, queues, daemons, cron jobs, or scheduled loops.

## Architecture

The controller lives in `darwin.research_loop`. It coordinates:

- `ResearchPlanner`
- `AcquisitionService`
- `SourceContentService`
- `AssistedEvidenceExtractionService`
- `AssistedClaimConstructionService`
- `ClaimValidationService`
- `StructuredSynthesisService`
- `NarrativeSynthesisService`

The controller does not duplicate these services. It persists loop-level state, query records, counters, events, stop reasons, and result links.

## Persistence

`research_loop_executions` stores the top-level execution record: request payload, mode, state, current stage, iteration count, budgets, counters, providers, stop reason, completion assessment, linked `ResearchRun`, synthesis/report IDs, warnings, errors, timestamps, and method version.

`research_loop_events` is append-only. Each event has a sequence number scoped to the execution, stage, event type, status, message, linked object IDs, counters, warnings, errors, and timestamp.

`research_loop_queries` stores bounded acquisition queries derived from the approved plan item and research question. There are no hidden search prompts or recursive query chains.

## Modes

`MANUAL_GATE` stops at `WAITING_EVIDENCE_APPROVAL`, `WAITING_CLAIM_APPROVAL`, and, when report publication is requested, `WAITING_SYNTHESIS_PUBLICATION`.

`AUTO_GROUNDED` uses existing acceptance APIs with `AUTO_ACCEPTED` audit modes after candidate validation. Evidence and Claim provenance checks still run.

`DRY_RUN` creates only loop execution/event records and returns `DRY_RUN_COMPLETE` with `INCOMPLETE`.

## Budgets And Counters

Counters are stored on the execution and copied into events:

```text
iterations
searches
source_candidates
sources_registered
content_fetches
segments_processed
evidence_proposals
accepted_evidence
claim_proposals
accepted_claims
provider_calls
tokens
cost
```

The controller compares request budgets to system maxima from settings before starting. Runtime checks occur between stages and before provider/service-boundary calls where practical.

## Resume And Recovery

Supported resume points:

- `WAITING_EVIDENCE_APPROVAL`
- `WAITING_CLAIM_APPROVAL`
- `WAITING_SYNTHESIS_PUBLICATION`

Resume is explicit through `ResearchLoopController.resume()` or `darwin research loop-resume`. Completed canonical actions are not replayed blindly. Existing candidate acceptance services provide idempotency for accepted Evidence and Claims.

If an operator accepts Evidence outside the loop before resuming, the controller synchronizes satisfied plan items from accepted Evidence candidates so claim construction can continue without duplicating canonical Evidence.

## Provider Failures

Existing provider retry behavior remains owned by the provider/service layer. The loop catches provider failures and stops with `PROVIDER_FAILURE`. It does not add infinite retry loops or provider-directed tool execution.

## Transaction Behavior

The loop is not designed as one giant transaction. Prior successful canonical records can remain if a later stage stops or fails. The execution state and events must reflect the real committed boundary reached.

Each controller call runs inside the caller's session boundary. CLI commands use the existing `session_scope()` helper.

## Commands

```bash
darwin research loop-start "Question?" --mode manual-gate
darwin research loop-start "Question?" --mode auto-grounded --publish-report
darwin research loop-start "Question?" --mode dry-run
darwin research loop-show <execution-id>
darwin research loop-events <execution-id>
darwin research loop-list --research-run-id <research-run-id-or-public-id>
darwin research loop-resume <execution-id>
```

Useful flags:

```text
--max-iterations
--max-searches
--max-sources
--max-fetched-sources
--publish-report
```

The CLI prints state, stage, stop reason, completion assessment, consumed counters, output IDs/artifact path, warnings, errors, and pending action. `loop-list` is read-only and prints persisted execution summaries for one ResearchRun: execution id, mode, state, stop reason, completion assessment, iteration count, counters, linked synthesis/report ids, and latest event timestamp. It does not print provider secrets.

## Observability

Database events are the authoritative loop audit trail. Runtime logs are useful operationally, but correctness must be inspectable from persisted execution and event records.

## Security

Research content and provider output are untrusted data. Providers cannot choose Darwin tools, shell commands, database queries, filesystem paths, or network targets. The controller chooses the next stage according to the request, budgets, and fixed state machine.

The loop does not persist secrets. Provider payloads store identifiers and model/configuration metadata only.

## Operational Recovery

When a loop stops at a manual gate, inspect candidates with existing Evidence/Claim/synthesis commands, accept or reject explicitly, then resume the loop. When a loop stops for budget, contradiction, human review, or provider failure, start a new execution or perform the required manual review; do not mutate the stopped execution into a different policy.
