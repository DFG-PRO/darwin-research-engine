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
integration tests in `tests/test_monetization.py`, `tests/test_portfolio_01.py`,
`tests/test_target_grouper.py`, and `tests/test_metric_readiness.py`.
Tests verify:
- Complete no-imputation behavior for omitted economic ranges;
- Positive evidence gates for `ACTIONABLE` state;
- Horizon isolation for 30-day and 90-day Daniel-hour ratios;
- Withholding EV when capital is at risk without modeled loss probability;
- Identification and aliasing of `research_targets`;
- Blocker fail-closed enforcement;
- Identity uniqueness and range boundary validation;
- Strict compliance with Portfolio 01 baseline invariants (12 opportunities, zero actionable, 3 blocked, 9 needs-evidence);
- Deterministic research target compression into structured research packages with zero atomic target loss;
- Epistemic metric readiness assessment preventing premature revenue unlocking from market benchmarks alone.

## Portfolio 01 Baseline Specification

Portfolio 01 establishes Darwin's canonical comparison baseline across 12 bounded DFG monetization paths.

### Purpose
The objective of Portfolio 01 is to evaluate real DFG commercial opportunities against a unified, evidence-aware decision framework without converting hypotheses into facts or imputing missing economic data.

### The 12 Canonical Opportunities
1. `fp-labs-external-services`: Technical consulting, software engineering, and workflow automation services for external clients.
2. `commercial-product-photography`: Commercial studio, e-commerce, and product photography services.
3. `cinema-collection-equipment-rental`: Peer-to-peer and commercial rental of high-end cinema and camera production equipment.
4. `production-engine-acceleration`: Creative media production workflow acceleration using automated rendering and batch workflow tools from Billy Production Engine.
5. `trading-strategy-hardening`: Hardening and paper-validating existing EMA trend, RSI mean-reversion, and VWAP strategies from Trading Dashboard via Trade Executor infrastructure.
6. `fpcriptoclub-monetization`: Monetization of crypto community audience through affiliate programs, VIP subscription channels, and digital products.
7. `billy-the-trader`: Fictional automated trading character brand monetization via synthetic media and automated content generation.
8. `airbnb-experiences-photography`: Local guided photo-walks and photography experiences booked via Airbnb Experiences.
9. `section-8-real-estate`: Acquisition, renovation, and operation of residential properties subsidized under the Section 8 housing choice voucher program.
10. `prediction-markets-latam`: Exchange or platform concept for Latin American event contracts and prediction markets.
11. `arbitrage-engine`: Systematic cross-venue or statistical arbitrage strategies across digital asset exchanges.
12. `tiktok-shop-affiliate-creative`: E-commerce affiliate commissions on TikTok Shop driven by AI-assisted product creative.

### No-Imputation Invariant & Unknown Semantics
- All 16 economic dimensions (time to first dollar, net revenue ranges for 30/90/180 days, upfront capital, capital at risk, Daniel hours for 30/90 days, margins, success probability, and qualitative risk/complexity scores) remain strictly `None` until validated empirical evidence exists.
- Darwin enforces zero economic imputation: missing values are never replaced with placeholder defaults or speculative estimates.
- Derived metrics (`score`, `expected_value_90_day_usd`, `revenue_per_daniel_hour_90_day`, `revenue_per_daniel_hour_30_day`) evaluate to `None` when required inputs are absent.

### Evidence Provenance Rules
- Concrete documentation references (`evidence_refs`) are included only when verifiable provenance exists in the repository tree (e.g. `docs/runtime/profitability-decision-framework.md` for `trading-strategy-hardening` and `arbitrage-engine`).
- Opportunities without existing canonical documentation have empty `evidence_refs`. Ad-hoc search conclusions or unverified claims are never accepted as canonical evidence.

### Status and Actionability Gates
- Zero opportunities qualify as `ACTIONABLE` at baseline: an opportunity cannot become actionable through missing evidence or absence of contrary proof.
- 3 opportunities evaluate to `BLOCKED`:
  - `arbitrage-engine`: Blocked by the Arbitrage Dependency Gate (requires validated market and liquidity evidence before implementation).
  - `prediction-markets-latam`: Blocked by regulatory and licensing requirements for wagering/event contracts.
  - `section-8-real-estate`: Blocked by upfront capital acquisition and financing prerequisites.
- The remaining 9 opportunities evaluate to `NEEDS_EVIDENCE`.

### Research Target Semantics
- Every unmeasured economic dimension and missing evidence requirement for `NEEDS_EVIDENCE` opportunities is systematically emitted as a machine-readable target in `result.research_targets` using `{opportunity_id}:{missing_metric}` format.
- These targets form the direct input to `RESEARCH_BACKLOG_01`.

### Research Target Grouper & Compression Architecture
To prevent operational fragmentation across 160 independent atomic tasks, Darwin provides a deterministic grouping service: `ResearchTargetGrouper` in `darwin.monetization.grouper`.
- Clusters atomic targets into 6 cohesive categories:
  - `PRICING_AND_REVENUE`: Net revenue ranges (30/90/180 days), gross margin, recurring revenue.
  - `CAPITAL_AND_RISK`: Upfront capital, capital at risk.
  - `OPERATIONAL_BANDWIDTH`: Time to first dollar, Daniel hours (30/90 days), operational complexity.
  - `MARKET_AND_GOVERNANCE_RISK`: Success probability, legal compliance, platform dependency.
  - `CAPABILITY_LEVERAGE`: Automation potential, DFG system reuse.
  - `EVIDENCE_PROVENANCE`: Explicit documentation references, market evidence baseline.
- Produces structured `ResearchPackage` instances containing the opportunity ID, package ID, title, objective, and bundled atomic fields.
- Achieves a ~5:1 compression ratio (reducing 160 atomic targets into 32 actionable research packages) with zero loss of atomic provenance or traceability.

### Metric Readiness Engine Architecture
Darwin enforces epistemic readiness gating via `MetricReadinessEngine` in `darwin.monetization.readiness`.
It deterministically assesses whether accumulated claims and evidence units are epistemically sufficient to populate an opportunity field:
- `READY_FOR_VALUE`: Concrete, verified point value justified by internal codebase or contract evidence.
- `READY_FOR_RANGE`: Bounded quantitative range supported by empirical testing or platform terms.
- `INSUFFICIENT_EVIDENCE`: Missing necessary evidentiary foundations.
- `REQUIRES_OPERATOR_DATA`: Requires internal operator schedule, personal asset inventory, or rate confirmation.
- `REQUIRES_EMPIRICAL_TEST`: Missing conversion, win rate, or sales cycle latency data.
- `BLOCKED_BY_DEPENDENCY`: Opportunity has active unresolved blockers.
The engine strictly enforces that external market pricing benchmarks alone cannot unlock expected net revenue projections without empirical conversion or contracted volume.

### Research Package Adapter Architecture
Darwin connects compressed research packages to execution channels via `ResearchPackageAdapter` in `darwin.monetization.adapter`.
- Converts each `ResearchPackage` into an actionable `ResearchPackageObjective` while maintaining 100% provenance back to `atomic_target_ids`, `package_id`, and `opportunity_id`.
- Categorizes research execution into four distinct mechanisms via `PackageObjectiveType`:
  - `OPERATOR_INTAKE`: Internal operator commitments, owned equipment inventory, past deliverables, or subscriber metrics.
  - `INTERNAL_AUDIT`: Codebase inspection, repository audits, or existing architectural validation.
  - `WEB_RESEARCH`: Primary web sources, platform fee schedules, and market pricing benchmarks.
  - `EMPIRICAL_VALIDATION`: Forward paper validation, execution latency tests, or empirical conversion measurements.
- Strictly prevents invalid web substitution: packages marked with `requires_operator_input` refuse conversion to web research loops and emit structured operator instructions instead.
- Retains jurisdiction tags (e.g. `US` for Section 8 HUD FMRs, `LATAM` for prediction markets).
- Enforces opportunity blocker gates: blocked objectives cannot launch research loops until upstream blockers are resolved.

### Evidence Intake Architecture
Incoming evidence from all channels enters Darwin via `EvidenceIntakeAdapter` in `darwin.monetization.intake`.
- Validates raw `EvidenceIntakePayload` instances across five canonical intake sources: `INTERNAL_REPOSITORY`, `OPERATOR`, `PRIMARY_WEB_SOURCE`, `EMPIRICAL_TEST`, and `EXTERNAL_MARKET_BENCHMARK`.
- Generates deterministic hash identifiers (`EV_{hash}`) and content fingerprints using `sha256_text` to prevent duplicate ingestion and track provenance.
- Enforces epistemic integrity: `EXTERNAL_MARKET_BENCHMARK` can never be classified as `FACT`; it remains strictly `SOURCE_CLAIM` or `DERIVED_VALUE`.
- Rejects missing sources, empty statements, inverted ranges (`range_min > range_max`), and negative inputs for non-negative metrics.
- Converts canonical Darwin `EvidenceRead` and `ClaimRead` objects into normalized `MetricEvidenceUnit` records.

### Portfolio Proposal Engine Architecture
Darwin prevents research loops from automatically mutating canonical opportunities through `PortfolioProposalEngine` in `darwin.monetization.proposal`.
- Acts as the safety boundary: evidence and readiness assessments evaluate to explicit, reviewed proposals rather than direct state mutation.
- Generates `PortfolioMetricProposal` records with five discrete deterministic actions:
  - `KEEP_NONE`: Default safe action when evidence is absent, insufficient, or lacks empirical conversion foundations. Retains `None` to prevent false precision.
  - `PROPOSE_VALUE`: Justified point value supported by verifiable contracts or confirmed assets.
  - `PROPOSE_RANGE`: Bounded candidate range derived from empirical testing, pricing benchmarks, and platform fees.
  - `FLAG_CONFLICT`: Contradictory evidence detected across sources; requires human review with zero silent selection.
  - `BLOCKED`: Upstream opportunity blockers active; rejects proposal generation.
- Enforces strict derivation gates:
  - Market prices alone propose `KEEP_NONE` for expected revenue.
  - Technical capabilities alone propose `KEEP_NONE` for commercial revenue.
  - Revenue ranges strictly require empirical conversion + pricing + platform fee evidence.
  - Mismatched or stale jurisdictions fail closed with `KEEP_NONE`.
  - All proposals default to `requires_human_review = True`.

### Limitations
1. Baseline fixture reflects pre-research uncertainty: no opportunity is marked actionable without validated numbers.
2. Value-of-information (VOI) weighting is deferred to research backlog prioritization.
3. Blockers are strictly enforced and cannot be overridden by speculative return projections.

## Current Roadmap

NOW:

1. establish deterministic opportunity representation;
2. preserve unknown values and evidence quality (no imputation);
3. expose missing research inputs (`research_targets`);
4. represent Portfolio 01 baseline across 12 DFG opportunities with explicit unknowns;
5. validate against representative DFG opportunity fixtures and Portfolio 01 invariants.

NEXT:

1. connect research targets to Darwin research planning (`RESEARCH_BACKLOG_01`);
2. execute first bounded evidence-gathering batch for high-impact unknowns;
3. add bull/base/bear scenario representation;
4. add explicit 30/90/180-day net-revenue confidence reporting.

LATER:

1. recurring portfolio refresh;
2. automated evidence aging;
3. opportunity discovery;
4. Alfred-facing portfolio summaries;
5. Lucius task generation after explicit governance gates.
