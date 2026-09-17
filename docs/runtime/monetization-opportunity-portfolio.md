# Monetization Opportunity Portfolio

Darwin's Monetization Opportunity Portfolio provides a deterministic,
evidence-aware comparison layer for business and revenue opportunities across
the DFG Universe.

Its purpose is to reduce time to credible net revenue without converting
assumptions into facts or imputing missing economic data.

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

## Core Economic Dimensions & Explicit Unknown Semantics

Each opportunity preserves ranges and confidence rather than false precision.
Crucially, all economic range inputs support explicit `None` when genuinely
unknown:

- `time_to_first_dollar_days`: OpportunityRange | None
- `expected_30_day_net_revenue_usd`: OpportunityRange | None
- `expected_90_day_net_revenue_usd`: OpportunityRange | None
- `expected_180_day_net_revenue_usd`: OpportunityRange | None
- `upfront_capital_usd`: OpportunityRange | None
- `capital_at_risk_usd`: OpportunityRange | None
- `daniel_hours_first_30_days`: OpportunityRange | None
- `daniel_hours_first_90_days`: OpportunityRange | None
- `gross_margin_pct`: OpportunityRange | None
- `recurring_revenue_pct`: OpportunityRange | None
- `probability_of_success`: float | None (0.0 to 1.0)
- `automation_potential`: int | None (1 to 5)
- `dfg_capability_reuse`: int | None (1 to 5)
- `legal_compliance_risk`: int | None (1 to 5)
- `platform_dependency_risk`: int | None (1 to 5)
- `operational_complexity`: int | None (1 to 5)

Darwin strictly refuses to manufacture placeholder values or default assumptions.
If an input is unknown, it remains `None`.

## Evidence Policy

Darwin must not manufacture missing economic inputs.

Missing values remain missing.

A numeric monetization score is emitted only when all required inputs for the
deterministic scoring model are explicitly supplied. If any required scoring
dimension or economic range is missing, `score` remains `None`.

Evidence quality is represented separately from economic projections.
An attractive projection is not evidence that the projection is true.

Evidence states:

- `INSUFFICIENT`
- `HYPOTHESIS`
- `PRELIMINARY`
- `VALIDATED`
- `OPERATING`

## Decision States & ACTIONABLE Evidence Gate

`ACTIONABLE`

An opportunity is never marked `ACTIONABLE` simply because negative evidence is
absent. It strictly requires positive evidence and complete quantitative inputs:
1. Evidence quality of `PRELIMINARY`, `VALIDATED`, or `OPERATING`;
2. Explicit `evidence_refs` (non-empty);
3. A fully computed, non-None `score` (all 6 scoring dimensions, time to first dollar, and upfront capital present);
4. Explicit `expected_90_day_net_revenue_usd` range;
5. Explicit `probability_of_success`;
6. Zero blockers.

A `None` monetization score or missing economic projection never qualifies as
actionable.

`NEEDS_EVIDENCE`

The opportunity lacks sufficient evidence, explicit references, or required
economic inputs. Darwin exposes every missing element in `missing_evidence` and
`research_targets` instead of inventing data.

`BLOCKED`

An explicit blocker prevents action. Examples include legal, compliance, capital,
dependency, or authorization gates. A high score never overrides a blocker.

## Expected Value & Loss Distribution Semantics

Expected value is evaluated strictly without inventing loss probabilities.

When `probability_of_success` and `expected_90_day_net_revenue_usd` are supplied:
- If `capital_at_risk_usd` has zero exposure (`midpoint == 0.0`), expected value is legitimately computed as:
  `midpoint(expected_90_day_net_revenue_usd) * probability_of_success`
- If `capital_at_risk_usd` is greater than zero, but no explicit loss probability distribution or loss severity is modeled:
  `expected_value_90_day_usd` is withheld as `None`.

Darwin refuses to subtract 100% of capital at risk as if it were a certain loss,
and refuses to invent an arbitrary probability of loss (such as assuming failure
severity equals 100% of capital at risk). Upfront capital and capital at risk
remain strictly separate.

## Daniel-Hour Horizon Semantics

Time horizons are strictly separated and never mixed:
- `revenue_per_daniel_hour_90_day`:
  Evaluated only when both `expected_90_day_net_revenue_usd` and `daniel_hours_first_90_days` are provided:
  `midpoint(expected_90_day_net_revenue_usd) / midpoint(daniel_hours_first_90_days)`
- `revenue_per_daniel_hour_30_day`:
  Evaluated only when both `expected_30_day_net_revenue_usd` and `daniel_hours_first_30_days` are provided:
  `midpoint(expected_30_day_net_revenue_usd) / midpoint(daniel_hours_first_30_days)`

Darwin never divides 90-day revenue by 30-day hours. If matching horizon hours
are absent, the respective metric remains `None`.

## Research Target Semantics

For opportunities in the `NEEDS_EVIDENCE` state, missing evidence items are
emitted under `research_targets` in `{opportunity_id}:{missing_field}` format.

Because value-of-information (VOI) ranking across research targets is not yet
modeled, the field is accurately titled `research_targets` rather than claiming
to be "highest value." To preserve backward compatibility with existing callers,
`highest_value_research_targets` is maintained as an alias synchronized with
`research_targets`.

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

## Limitations

1. **Deterministic Diagnostic**: Computations are static diagnostics comparing bounded fixtures, not dynamic Monte Carlo simulations or accounting statements.
2. **Binary Risk Simplification**: Without explicit loss distributions, non-zero capital at risk prevents EV computation.
3. **No Autonomous Research**: Missing targets are exposed for research planning but are not retrieved autonomously in this layer.

## Validation

The monetization portfolio implementation is verified via deterministic unit and
integration tests in `tests/test_monetization.py`.
Tests verify:
- Complete no-imputation behavior for omitted economic ranges;
- Positive evidence gates for `ACTIONABLE` state;
- Horizon isolation for 30-day and 90-day Daniel-hour ratios;
- Withholding EV when capital is at risk without modeled loss probability;
- Identification and aliasing of `research_targets`;
- Blocker fail-closed enforcement;
- Identity uniqueness and range boundary validation.

## Current Roadmap

NOW:

1. establish deterministic opportunity representation;
2. preserve unknown values and evidence quality (no imputation);
3. expose missing research inputs (`research_targets`);
4. compare time-to-first-dollar, capital, revenue, Daniel-hours (matched horizons), risk, reuse, and automation;
5. validate against representative DFG opportunity fixtures.

NEXT:

1. connect research targets to Darwin research planning (Research Backlog 01);
2. represent Portfolio 01 baseline with explicit unknowns;
3. execute first bounded evidence-gathering batch;
4. add bull/base/bear scenario representation;
5. add explicit 30/90/180-day net-revenue confidence reporting.

LATER:

1. recurring portfolio refresh;
2. automated evidence aging;
3. opportunity discovery;
4. Alfred-facing portfolio summaries;
5. Lucius task generation after explicit governance gates.
