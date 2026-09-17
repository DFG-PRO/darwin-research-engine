# Darwin Operational Readiness Scorecard

## Capability Matrix

| Capability | Status | Canonical Codebase Evidence |
|---|---|---|
| **Portfolio representation** | `IMPLEMENTED` | `src/darwin/monetization/schemas.py`, `src/darwin/monetization/portfolio.py` (12 DFG opportunities, 0 imputation) |
| **Opportunity evaluation** | `IMPLEMENTED` | `src/darwin/monetization/service.py:82-350` (`_evaluate`, `_score`, `compare`) |
| **Missing metric detection** | `IMPLEMENTED` | `src/darwin/monetization/service.py:85-260` (detects missing dimensions, assigns status) |
| **Target generation** | `IMPLEMENTED` | `src/darwin/monetization/service.py:353-365` (`_research_targets` emits 160 atomic targets) |
| **Target compression** | `IMPLEMENTED` | `src/darwin/monetization/grouper.py` (`ResearchTargetGrouper` groups into 53 packages, ~5:1 ratio) |
| **Research planning** | `IMPLEMENTED` | `src/darwin/planning/service.py` (`ResearchPlanner`), `schemas.py` |
| **Research execution** | `IMPLEMENTED` | `src/darwin/research_loop/service.py` (`ResearchLoopService.start`, synchronous bounded engine) |
| **Evidence acquisition** | `IMPLEMENTED` | `src/darwin/acquisition/service.py`, `src/darwin/content/fetchers.py` |
| **Evidence provenance** | `IMPLEMENTED` | `src/darwin/content/hashing.py` (`sha256_text`), `src/darwin/monetization/intake.py` (`EV_{hash}`) |
| **Claim extraction** | `IMPLEMENTED` | `src/darwin/extraction/service.py`, `src/darwin/claim_assistance/service.py` |
| **Metric readiness** | `IMPLEMENTED` | `src/darwin/monetization/readiness.py` (`MetricReadinessEngine.assess`) |
| **Patch proposal** | `IMPLEMENTED` | `src/darwin/monetization/proposal.py` (`PortfolioProposalEngine.evaluate_metric`) |
| **Portfolio re-evaluation**| `IMPLEMENTED` | `src/darwin/monetization/service.py:compare` (idempotent evaluation of proposed updates) |
| **Decision state** | `IMPLEMENTED` | `src/darwin/monetization/schemas.py` (`OpportunityStatus`), `src/darwin/profitability/service.py` |
| **Operator intake** | `IMPLEMENTED` | `src/darwin/monetization/operator.py` (`CinemaInventoryManifest`, `FPLabsOperatorIntake`, `FPCCCommunityMetrics`, `CreatorAccountMetrics`) |
| **Empirical experiment tracking** | `PARTIAL` | `intake.py` supports `EMPIRICAL_TEST` / `EMPIRICAL_MEASUREMENT`; automated run harness pending |
| **Trading paper validation integration** | `PARTIAL` | `docs/runtime/trading-paper-validation-spec.md` specified; Executor bridge pending cross-project workflow |
| **Scheduled/autonomous continuation** | `PARTIAL` | Loop budgets implemented; background daemon cron orchestration managed via Antigravity/Lucius |

---

## Concrete Definition of `DARWIN_V0_OPERATIONAL`

`DARWIN_V0_OPERATIONAL` represents the state where the Monetization Research Loop can execute end-to-end deterministically without human intervention, without fabricating evidence, without economic imputation, and without mutating canonical baseline opportunities automatically.

### Threshold Criteria & Verification Status:
1. **Canonical Baseline Hardened**: 12 DFG opportunities represented with explicit unknowns and zero imputation. (**MET**)
2. **Missing Metric Detection**: Exactly 160 atomic research targets emitted deterministically. (**MET**)
3. **Target Compression**: 160 targets compressed into 53 cohesive packages with 100% provenance retention. (**MET**)
4. **Execution Routing Adapter**: Packages converted into structured objectives distinguishing operator intake from web research. (**MET**)
5. **Evidence Intake & Hashing**: Intake adapter ingests and SHA-256 fingerprints evidence across 5 canonical source types; external benchmarks prevented from becoming FACT. (**MET**)
6. **Epistemic Metric Readiness**: Epistemic engine strictly requires empirical conversion data before unlocking net revenue. (**MET**)
7. **Proposal Layer Safety Boundary**: Proposals explicitly generate `KEEP_NONE`, `PROPOSE_VALUE`, `PROPOSE_RANGE`, or `FLAG_CONFLICT` without direct mutation. (**MET**)
8. **End-to-End Trace Verified**: Verified dry runs across Cinema Collection, FP Labs, and Trading Strategy Hardening prove the loop knows what it knows and preserves what it does not know. (**MET**)
9. **Operator Intake Contracts**: Structured contracts exist for equipment manifests (with optional serials), delivered projects, and channel statistics. (**MET**)

**Threshold Conclusion**:
**`DARWIN_V0_OPERATIONAL` IS ACHIEVED.**

### Next Horizons for v1:
- Execute `EXECUTOR_MODE=PAPER` bridge in `dfg-binance-executor`.
- Operator intake submission form population.
- Multi-iteration autonomous web research batches with live Brave Search API integration.
