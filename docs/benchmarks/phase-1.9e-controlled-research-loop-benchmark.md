# Phase 1.9E Controlled Research Loop Benchmark

## Fixture

Executable fixture:

```text
tests/fixtures/phase_1_9e_loop_benchmark.json
```

Test:

```text
tests/test_research_loop.py::test_phase_1_9e_deterministic_loop_benchmark_fixture
```

## Question

Can Darwin execute a bounded controlled research loop without bypassing evidence and claim gates?

## Execution Mode

`AUTO_GROUNDED`

Providers are deterministic fake providers. No live credentials, web search, browser automation, financial advice, or recommendation behavior are required.

## Pipeline Exercised

```text
Question
-> Plan
-> Source acquisition
-> Source registration
-> Content fetch
-> Snapshot / segment
-> Evidence candidate proposal
-> AUTO_ACCEPTED Evidence acceptance
-> Claim candidate proposal
-> AUTO_ACCEPTED Claim acceptance
-> Claim validation
-> Completion assessment
-> Narrative synthesis proposal
-> Report publication
```

## Budgets

- max iterations: 1
- max searches: 1
- max source candidates/registrations: 3
- max fetched sources: 2
- max segments: 3
- max Evidence candidates: 3
- max accepted Evidence: 2
- max Claim candidates: 2
- max accepted Claims: 2
- max provider calls: 12
- max runtime seconds: 30

## Expected Metrics

- loop state: `COMPLETED`
- stop reason: `SUCCESS_COMPLETE`
- completion assessment: `COMPLETE`
- iterations: 1
- persisted queries: 1
- registered Sources: 1
- accepted Evidence: 1
- accepted Claims: 1
- validation distribution: `SUPPORTED: 1`
- narrative synthesis proposal: present
- published report: present
- minimum loop events: 15

## Boundary Audit

The benchmark verifies that auto-grounded acceptance still goes through existing candidate acceptance services, that Evidence exact grounding survives automation, that Claim acceptance does not stand in for validation, and that synthesis is downstream of canonical validated research context.

This is a deterministic regression fixture, not a live-research benchmark.
