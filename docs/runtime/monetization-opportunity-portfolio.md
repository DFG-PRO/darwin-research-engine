# Monetization Opportunity Portfolio

Darwin's Monetization Opportunity Portfolio provides a deterministic,
evidence-aware comparison layer for business and revenue opportunities across
the DFG Universe.

Its purpose is to reduce time to credible net revenue without converting
assumptions into facts.

## Scope

The portfolio may compare opportunities such as:

- services and FP Labs work;
- production and photography;
- Cinema Collection;
- content and affiliate businesses;
- Product Engine opportunities;
- trading-related business paths;
- real-estate opportunities;
- new platforms or products;
- other bounded DFG opportunities.

Trading-strategy profitability remains in `darwin.profitability`.
This module compares broader monetization opportunities and does not replace
the trading profitability framework.

## Core Economic Dimensions

Each opportunity preserves ranges and confidence rather than false precision:

- time to first dollar;
- expected 30-day net revenue;
- expected 90-day net revenue;
- expected 180-day net revenue;
- upfront capital;
- capital at risk;
- Daniel-hours required during the first 30 days;
- gross margin;
- recurring-revenue potential;
- probability of success;
- automation potential;
- DFG capability reuse;
- legal/compliance risk;
- platform dependency risk;
- operational complexity.

## Evidence Policy

Darwin must not manufacture missing economic inputs.

Missing values remain missing.

A numeric score is emitted only when the inputs required by the deterministic
scoring model are explicitly supplied.

Evidence quality is represented separately from the economic projections.
An attractive projection is not evidence that the projection is true.

Evidence states:

- `INSUFFICIENT`
- `HYPOTHESIS`
- `PRELIMINARY`
- `VALIDATED`
- `OPERATING`

## Decision States

`ACTIONABLE`

The opportunity has at least preliminary evidence, explicit evidence
references, a supplied probability estimate, and no explicit blocker.

`NEEDS_EVIDENCE`

The opportunity lacks sufficient evidence or a required decision input.
Darwin exposes the missing evidence instead of inventing it.

`BLOCKED`

An explicit blocker prevents action. Examples may include legal, compliance,
capital, dependency, or authorization gates.

A high score never overrides a blocker.

## Expected Value

The v1 90-day expected-value diagnostic is deliberately simple:

`midpoint(90-day net revenue) * probability_of_success - midpoint(capital_at_risk)`

It is a comparison diagnostic, not a forecast or accounting statement.

Upfront capital and capital at risk remain separate.

## Daniel-Hour Efficiency

Darwin also exposes:

`midpoint(90-day net revenue) / midpoint(first-30-day Daniel-hours)`

This is intended to identify opportunities that may generate meaningful
revenue without creating a permanently manual business.

## Research Integration

The v1 module is deterministic and does not autonomously research missing
values.

For `NEEDS_EVIDENCE` opportunities it emits explicit research targets.
Those targets are intended to become inputs to Darwin's canonical research
loop in a later bounded integration.

Research results must eventually enter the portfolio through canonical
Evidence/Claim provenance rather than through unsupported model assertions.

## Authority Boundary

This capability does not authorize:

- spending money;
- purchasing subscriptions;
- signing contracts;
- contacting customers;
- publishing content;
- trading;
- moving funds;
- changing credentials;
- deploying production systems;
- modifying other DFG repositories.

It is a decision-support capability only.

## Current Roadmap

NOW:

1. establish deterministic opportunity representation;
2. preserve unknown values and evidence quality;
3. expose missing research inputs;
4. compare time-to-first-dollar, capital, revenue, Daniel-hours, risk, reuse,
   and automation;
5. validate against representative DFG opportunity fixtures.

NEXT:

1. connect research targets to Darwin research planning;
2. map canonical Evidence and Claims into opportunity inputs;
3. add bull/base/bear scenario representation;
4. add explicit 30/90/180-day net-revenue confidence reporting;
5. add portfolio persistence and historical comparison if operational use
   demonstrates that persistence is necessary.

LATER:

1. recurring portfolio refresh;
2. automated evidence aging;
3. opportunity discovery;
4. Alfred-facing portfolio summaries;
5. Lucius task generation after explicit governance gates.

The system must earn these additional capabilities through demonstrated use.
