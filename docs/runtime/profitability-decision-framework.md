# Profitability Decision Framework

This runtime framework supports Darwin's controlled operating handoff for trading research.
Its objective is to minimize time to credible positive expectancy while preserving evidence
quality, capital, reproducibility, and operational safety.

It does not authorize live-money execution, exchange credential changes, withdrawals,
deposits, leverage changes on real accounts, production deployment, push, merge, or
multi-worker orchestration.

## Current DFG State

- Darwin Research Engine has canonical research persistence, planning, acquisition,
  source-content, evidence extraction, claim construction, synthesis, narrative report,
  bounded loop, and observability foundations.
- Darwin does not yet contain trading-specific profitability models, recommendation
  logic, arbitrage models, paper-trading integrations, or live execution authority.
- Trade Executor contains Binance Futures webhook execution plumbing and operational
  safety documentation, but it is execution infrastructure, not research evidence that a
  strategy has positive expectancy.
- Trading Dashboard contains active strategy and backtesting code for EMA trend, RSI
  mean reversion, VWAP, translated Pine strategies, and a backtest engine. The official
  checkout observed during this handoff was not canonical-clean, so it is usable as
  repository evidence but not as a clean mutation target.
- No Arbitrage Engine repository was found in the observed local DFG project tree.

## Candidate Path Classes

Darwin compares:

- `EXISTING_STRATEGY`: harden and validate strategies already present in DFG systems.
- `ARBITRAGE`: cross-exchange, triangular, spot/futures, funding, basis, statistical, or
  relative-value paths only when evidence supports the category.
- `OTHER_SYSTEMATIC`: another bounded systematic opportunity if evidence shows a shorter
  time to credible positive expectancy.
- `HYBRID`: a sequence that uses Darwin research plus a minimal implementation component
  when dependency gates justify it.

## Economic Comparison Dimensions

Each candidate path is evaluated with ranges rather than false precision:

- `TIME_TO_PAPER_VALIDATION`
- `TIME_TO_CONTROLLED_LIVE_VALIDATION`
- `ENGINEERING_EFFORT`
- `RESEARCH_CONFIDENCE`
- `CAPITAL_REQUIRED`
- `EXPECTED_RETURN_RANGE`
- `EXPECTED_DRAWDOWN`
- `TAIL_RISK`
- `OPERATIONAL_COMPLEXITY`
- `DATA_REQUIREMENTS`
- `INFRASTRUCTURE_REQUIREMENTS`
- `DEPENDENCY_RISK`

The USD 2,000 unlevered scenario is required. A USD 2,000 scenario with up to 5x
notional exposure may be modeled when the strategy mechanics justify it, but the model
must keep capital, notional exposure, risk per trade, drawdown, and liquidation risk
separate.

The 7-10 percent monthly return band is not an objective assumption. Darwin reports it as
supported only when validated evidence exists; otherwise it remains `INSUFFICIENT_EVIDENCE`.

## Roadmap Reactivation

NOW:

- Compare existing strategy, Arbitrage, and other bounded systematic paths using explicit
  evidence and uncertainty.
- Add paper-validation preparation for the existing Dashboard strategy path because it is
  closer to executable evidence than greenfield Arbitrage.
- Capture realistic fee, spread, slippage, drawdown, sample-size, and regime assumptions
  before any controlled live validation.

NEXT:

- Import or reference Dashboard backtest outputs as Darwin evidence artifacts.
- Add deterministic cost-model checks for fees, spread, slippage, and funding.
- Add walk-forward and out-of-sample result summaries.
- Add paper-validation export formats that downstream systems can inspect without live
  authority.

LATER:

- Build an Arbitrage Engine repository only after Darwin evidence justifies the first
  implementation slice.
- Add normalized multi-venue order books, fee models, slippage models, opportunity
  representation, and simulation before any exchange credentials or order placement.

PARKED:

- Live-money execution, autonomous capital allocation, withdrawals, deposits, real leverage
  changes, production deployment, and multi-worker orchestration.

## Arbitrage Dependency Gate

Arbitrage implementation remains blocked until Darwin creates sufficient evidence:

1. Darwin research task defines the exact arbitrage category and market assumptions.
2. Darwin captures evidence for fees, spread persistence, liquidity, latency, funding,
   inventory requirements, withdrawal constraints, API limits, and execution risk.
3. Darwin validation gate marks the opportunity as at least paper-validation worthy.
4. A bounded Arbitrage engineering task becomes `READY`.
5. Lucius implements only the unlocked slice in an isolated workspace.
6. Tests and simulation results return to Darwin as evidence.
7. Darwin evaluates the result before another Arbitrage task is unlocked.

Without this gate, full Arbitrage implementation is deferred.

## CLI

Compare candidate paths from a supplied JSON payload:

```bash
darwin profitability compare profitability-comparison.json
darwin profitability compare profitability-comparison.json --format json
```

The command is read-only with respect to Darwin research persistence. Invalid input or an
unsupported output format fails closed.
