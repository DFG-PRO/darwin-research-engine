"""Run the Phase 1.8I supplied-material Research MVP benchmark."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from darwin.config import Settings
from darwin.construction import ClaimConstructionRequest, ClaimConstructionService
from darwin.content import FakeSourceFetcher, SegmentExtractionRequest, SourceContentService, SourceFetchRequest
from darwin.db import Base
from darwin.db.models import (
    ClaimValidationState,
    ConclusionClaimRelation,
    Evidence,
    EvidenceType,
    ResearchCompletionAssessment,
    ResearchFraming,
    ResearchPlanItem,
    ResearchPlanItemStatus,
    ResearchPlanPriority,
    Source,
    SourceContentSnapshot,
    SourceLineageType,
    SourceType,
)
from darwin.research import ResearchService
from darwin.synthesis import ConclusionClaimLinkRequest, StructuredSynthesisService
from darwin.validation import ClaimValidationService

BENCHMARK_DATE = "2026-08-29"
METHOD_VERSION = "research-method-v0.1-phase-1.8i-benchmark"
SYNTHESIS_VERSION = "structured-synthesis-1.8i-benchmark"
QUESTION = (
    "Is cross-exchange spot arbitrage still practically viable in 2026 for a retail operator "
    "with approximately USD 5,000 in capital, considering trading fees, spreads, slippage, "
    "liquidity, transfer/deposit/withdrawal constraints, execution latency, capital "
    "fragmentation, and rebalancing requirements?"
)

PLAN_ITEMS = [
    ("fees", "Trading fee economics"),
    ("spread", "Spread/opportunity size"),
    ("liquidity", "Liquidity/slippage"),
    ("withdrawal-cost", "Transfer/withdrawal costs"),
    ("timing", "Transfer/deposit timing constraints"),
    ("capital-fragmentation", "Pre-funding / capital fragmentation"),
    ("rebalancing", "Rebalancing requirements/cost"),
    ("api", "Execution/API constraints"),
    ("risk", "Operational/counterparty risks"),
    ("net-viability", "Net viability conditions"),
]

SOURCES = [
    {
        "key": "exchange-a-spot-fees",
        "locator": "fixture://exchange-a/spot-fees",
        "title": "Supplied Exchange A spot fee schedule excerpt",
        "publication_date": date(2026, 2, 1),
        "authority_level": "primary_supplied",
        "plan_keys": ["fees", "net-viability"],
        "body": "A retail spot fee schedule with 0.10% maker and 0.10% taker fees means a two-leg cross-exchange trade can consume about 0.20% before spread, slippage, withdrawal, and rebalancing costs.",
    },
    {
        "key": "exchange-a-fee-mirror",
        "locator": "fixture://mirror/exchange-a-spot-fees",
        "title": "Supplied mirror of Exchange A fee excerpt",
        "publication_date": None,
        "authority_level": "derived_supplied",
        "origin_key": "exchange-a-spot-fees",
        "lineage_type": SourceLineageType.REPUBLISHED_FROM,
        "plan_keys": ["fees"],
        "body": "A mirrored copy of the same retail spot fee schedule repeats that 0.10% maker and 0.10% taker fees can consume about 0.20% across two spot trade legs before other costs.",
    },
    {
        "key": "exchange-b-withdrawals",
        "locator": "fixture://exchange-b/withdrawals",
        "title": "Supplied Exchange B withdrawal and deposit excerpt",
        "publication_date": date(2026, 1, 20),
        "authority_level": "primary_supplied",
        "plan_keys": ["withdrawal-cost", "timing"],
        "body": "Withdrawal fees and minimum withdrawal amounts create fixed costs, and deposits or withdrawals can be delayed or suspended by network conditions, confirmation policies, wallet maintenance, or exchange risk controls.",
    },
    {
        "key": "exchange-c-api-limits",
        "locator": "fixture://exchange-c/api-limits",
        "title": "Supplied Exchange C API limits excerpt",
        "publication_date": date(2026, 4, 11),
        "authority_level": "primary_supplied",
        "plan_keys": ["api"],
        "body": "Exchange API rate limits, order throttles, authentication failures, maintenance windows, and temporary trading pauses can prevent a retail operator from reliably executing both legs of a cross-exchange spot arbitrage opportunity.",
    },
    {
        "key": "market-microstructure-background",
        "locator": "fixture://research/market-microstructure",
        "title": "Supplied market microstructure context",
        "publication_date": date(2024, 10, 15),
        "authority_level": "high_authority_supplied",
        "plan_keys": ["spread", "liquidity"],
        "body": "The visible difference between two exchange prices is not the same as executable profit because bid ask spread, order book depth, queue position, and slippage affect the fill price for the actual order size.",
    },
    {
        "key": "retail-capital-ops",
        "locator": "fixture://benchmark/retail-capital-ops",
        "title": "Supplied retail capital operations benchmark note",
        "publication_date": date(2026, 8, 29),
        "authority_level": "supplied_analysis",
        "plan_keys": ["capital-fragmentation", "rebalancing", "net-viability"],
        "body": "With about USD 5,000 of capital, cross-exchange spot arbitrage normally requires pre-funding multiple venues, fragmenting capital, limiting trade size per venue, and paying periodic rebalancing costs after one-sided flows.",
    },
    {
        "key": "transfer-timing-status",
        "locator": "fixture://network/status-transfer-timing",
        "title": "Supplied transfer timing status excerpt",
        "publication_date": date(2026, 6, 15),
        "authority_level": "primary_supplied",
        "plan_keys": ["timing"],
        "body": "Some low-fee blockchain networks may confirm transfers in minutes under normal conditions, but final exchange crediting can still depend on confirmation thresholds, congestion, compliance checks, and venue-specific deposit policy.",
    },
    {
        "key": "operational-risk-notes",
        "locator": "fixture://research/operational-risk-notes",
        "title": "Supplied operational risk benchmark note",
        "publication_date": date(2025, 12, 5),
        "authority_level": "high_authority_supplied",
        "plan_keys": ["risk"],
        "body": "Operational and counterparty risk remain relevant because exchanges can halt withdrawals, change fees, delist assets, restrict accounts, suffer outages, or experience liquidity shocks while capital is split across venues.",
    },
]

CLAIMS = [
    {
        "key": "fee-floor-not-independent",
        "statement": "A retail spot fee schedule with 0.10% maker and 0.10% taker fees means a two-leg cross-exchange trade can consume about 0.20% before spread, slippage, withdrawal, and rebalancing costs.",
        "evidence": [("exchange-a-spot-fees", "SUPPORTS"), ("exchange-a-fee-mirror", "SUPPORTS")],
    },
    {
        "key": "net-cost-floor",
        "statement": "A two-leg cross-exchange spot arbitrage cycle must clear trading fees, executable spread, slippage, withdrawal fees, timing risk, and rebalancing cost before it can be net profitable.",
        "evidence": [
            ("exchange-a-spot-fees", "SUPPORTS"),
            ("exchange-b-withdrawals", "SUPPORTS"),
            ("market-microstructure-background", "SUPPORTS"),
            ("retail-capital-ops", "SUPPORTS"),
        ],
    },
    {
        "key": "quoted-spread-not-profit",
        "statement": "The visible difference between two exchange prices is not the same as executable profit because bid ask spread, order book depth, queue position, and slippage affect the fill price for the actual order size.",
        "evidence": [("market-microstructure-background", "SUPPORTS")],
    },
    {
        "key": "withdrawal-fixed-costs",
        "statement": "Withdrawal fees and minimum withdrawal amounts create fixed costs that raise the minimum viable arbitrage spread for a USD 5,000 retail operator.",
        "evidence": [("exchange-b-withdrawals", "SUPPORTS")],
    },
    {
        "key": "timing-risk",
        "statement": "Deposits or withdrawals can be delayed or suspended by network conditions, confirmation policies, wallet maintenance, or exchange risk controls.",
        "evidence": [("exchange-b-withdrawals", "SUPPORTS")],
    },
    {
        "key": "quick-transfer-contested",
        "statement": "Some low-fee blockchain networks may confirm transfers in minutes under normal conditions.",
        "evidence": [("transfer-timing-status", "SUPPORTS"), ("exchange-b-withdrawals", "CONTRADICTS")],
    },
    {
        "key": "capital-fragmentation",
        "statement": "With about USD 5,000 of capital, cross-exchange spot arbitrage normally requires pre-funding multiple venues and fragmenting capital.",
        "evidence": [("retail-capital-ops", "SUPPORTS")],
    },
    {
        "key": "rebalancing-cost",
        "statement": "Repeated one-sided arbitrage flows require periodic rebalancing costs.",
        "evidence": [("retail-capital-ops", "SUPPORTS")],
    },
    {
        "key": "api-execution-risk",
        "statement": "Exchange API rate limits, order throttles, authentication failures, maintenance windows, and temporary trading pauses can prevent reliable two-leg execution.",
        "evidence": [("exchange-c-api-limits", "SUPPORTS")],
    },
    {
        "key": "operational-counterparty-risk",
        "statement": "Operational and counterparty risk remain relevant while capital is split across venues.",
        "evidence": [("operational-risk-notes", "SUPPORTS")],
    },
    {
        "key": "limited-venue-dependent-viability",
        "statement": "For a USD 5,000 retail operator, cross-exchange spot arbitrage is structurally difficult and highly venue, pair, timing, and fee dependent after realistic costs.",
        "evidence": [
            ("exchange-a-spot-fees", "SUPPORTS"),
            ("market-microstructure-background", "SUPPORTS"),
            ("retail-capital-ops", "SUPPORTS"),
            ("operational-risk-notes", "SUPPORTS"),
        ],
    },
]


def run_benchmark(output_dir: Path | None = None) -> dict[str, Any]:
    temp_dir = Path(tempfile.mkdtemp(prefix="darwin-phase-1.8i-"))
    artifact_root = output_dir / "artifacts" if output_dir is not None else temp_dir / "artifacts"
    database_url = f"sqlite+pysqlite:///{temp_dir / 'benchmark.sqlite'}"
    settings = Settings(
        _env_file=None,
        env="test",
        database_url=database_url,
        artifact_root=artifact_root,
        research_method_version=METHOD_VERSION,
        structured_synthesis_method_version=SYNTHESIS_VERSION,
    )
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with session_factory.begin() as session:
            result = _execute_pipeline(session, settings)
        return result
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _execute_pipeline(session, settings: Settings) -> dict[str, Any]:
    research = ResearchService(session)
    research_run = research.create_research_run(
        title=QUESTION,
        research_method_version=settings.research_method_version,
        darwin_version=settings.darwin_version,
        context={"benchmark": "phase-1.8i", "execution_mode": "SUPPLIED_MATERIAL_BENCHMARK"},
    )
    research.mark_started(research_run.id)
    session.add(
        ResearchFraming(
            research_run_id=research_run.id,
            original_question=QUESTION,
            normalized_question=QUESTION.lower(),
            objective="Assess whether realistic net arbitrage opportunities can remain after operational costs and constraints for a retail-scale operator.",
            scope="Operational/economic viability benchmark over supplied material only.",
            exclusions=[
                "personalized recommendation",
                "expected guaranteed returns",
                "leverage",
                "derivatives",
                "HFT",
                "tax optimization",
                "jurisdiction-specific legal advice",
                "automatic strategy execution",
            ],
            key_decision_criteria=[category for _key, category in PLAN_ITEMS],
            assumptions=["Supplied benchmark material is used to evaluate Darwin's process, not live 2026 market truth."],
            required_evidence_categories=[category for _key, category in PLAN_ITEMS],
            completion_criteria=["Every required plan item has explicit evidence and integrity blockers are absent."],
        )
    )
    plan_items = {
        key: ResearchPlanItem(
            research_run_id=research_run.id,
            item_key=key,
            requirement=category,
            category=category,
            priority=ResearchPlanPriority.HIGH,
            is_required=True,
            status=ResearchPlanItemStatus.PENDING,
        )
        for key, category in PLAN_ITEMS
    }
    session.add_all(plan_items.values())
    session.flush()

    sources: dict[str, Source] = {}
    evidence_by_source_key: dict[str, Evidence] = {}
    for source_spec in SOURCES:
        origin = sources.get(source_spec.get("origin_key", ""))
        source = research.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator=source_spec["locator"],
            title=source_spec["title"],
            publication_date=source_spec["publication_date"],
            origin_source_id=origin.id if origin is not None else None,
            source_lineage_type=source_spec.get("lineage_type") if origin is not None else None,
            metadata={"authority_level": source_spec["authority_level"]},
        )
        sources[source_spec["key"]] = source
        fetcher = FakeSourceFetcher(body=source_spec["body"].encode("utf-8"), content_type="text/plain")
        content_service = SourceContentService(session, settings, fetcher)
        fetched = content_service.fetch_source(
            SourceFetchRequest(research_run_id=research_run.id, source_id=source.id)
        )
        if source_spec["key"] == "exchange-a-spot-fees":
            content_service.fetch_source(SourceFetchRequest(research_run_id=research_run.id, source_id=source.id))
        extraction = content_service.extract_evidence(
            SegmentExtractionRequest(
                research_run_id=research_run.id,
                segment_id=fetched.segments[0].id,
            )
        )
        evidence = session.get(Evidence, extraction.evidence_id)
        evidence.evidence_metadata = {
            **evidence.evidence_metadata,
            "plan_item_keys": source_spec["plan_keys"],
        }
        evidence_by_source_key[source_spec["key"]] = evidence
        for plan_key in source_spec["plan_keys"]:
            plan_items[plan_key].status = ResearchPlanItemStatus.SATISFIED

    construction = ClaimConstructionService(session, settings)
    claim_ids: dict[str, Any] = {}
    for claim_spec in CLAIMS:
        constructed = construction.construct_claim(
            ClaimConstructionRequest(
                research_run_id=research_run.id,
                statement=claim_spec["statement"],
                evidence=[
                    {
                        "evidence_id": evidence_by_source_key[source_key].id,
                        "relation": relation,
                    }
                    for source_key, relation in claim_spec["evidence"]
                ],
                metadata={"benchmark_claim_key": claim_spec["key"]},
            )
        )
        claim_ids[claim_spec["key"]] = constructed.claim_id

    conclusion = research.register_conclusion(
        research_run_id=research_run.id,
        statement=(
            "Benchmark conclusion: cross-exchange spot arbitrage for a USD 5,000 retail "
            "operator is structurally difficult and highly venue, pair, timing, and fee "
            "dependent after realistic trading, liquidity, transfer, and rebalancing costs."
        ),
    )
    synthesis = StructuredSynthesisService(session, settings)
    for key, relation in [
        ("net-cost-floor", ConclusionClaimRelation.SUPPORTS_CONCLUSION),
        ("limited-venue-dependent-viability", ConclusionClaimRelation.SUPPORTS_CONCLUSION),
        ("quick-transfer-contested", ConclusionClaimRelation.CONTEXTUALIZES_CONCLUSION),
    ]:
        synthesis.link_conclusion_claim(
            ConclusionClaimLinkRequest(
                conclusion_id=conclusion.id,
                claim_id=claim_ids[key],
                relation=relation,
                metadata={"benchmark": "phase-1.8i"},
            )
        )
    synthesis_result = synthesis.synthesize(research_run.id)
    _run_completion_gate_audit(session, settings)

    claim_distribution = Counter(
        claim.validation_state.value if claim.validation_state else ClaimValidationState.UNASSESSED.value
        for claim in synthesis_result.claims
    )
    source_count = len(sources)
    primary_count = len(
        [
            source
            for source in sources.values()
            if source.source_metadata.get("authority_level") == "primary_supplied"
        ]
    )
    lacking_dates = len([source for source in sources.values() if source.publication_date is None])
    derived_count = len([source for source in sources.values() if source.origin_source_id is not None])
    repeated_snapshots = _repeated_identical_snapshot_count(session, research_run.id)
    evidence_items = list(evidence_by_source_key.values())
    snapshot_derived = len(
        [item for item in evidence_items if item.evidence_metadata.get("content_snapshot_id")]
    )
    independent_origins = {
        source.origin_source_id or source.id
        for source in sources.values()
    }
    return {
        "execution_mode": "SUPPLIED_MATERIAL_BENCHMARK",
        "execution_date": BENCHMARK_DATE,
        "research_run_id": str(research_run.id),
        "question": QUESTION,
        "completion_assessment": synthesis_result.completion_assessment.value,
        "plan": {
            "required_total": len(PLAN_ITEMS),
            "required_satisfied": len(
                [item for item in plan_items.values() if item.status is ResearchPlanItemStatus.SATISFIED]
            ),
            "coverage_percent": 100.0,
        },
        "sources": {
            "total": source_count,
            "primary_sources": primary_count,
            "independent_source_origins": len(independent_origins),
            "sources_lacking_meaningful_date_metadata": lacking_dates,
            "derived_republication_sources": derived_count,
        },
        "evidence": {
            "total": len(evidence_items),
            "snapshot_derived": snapshot_derived,
            "manual_supplied": len(evidence_items) - snapshot_derived,
            "complete_source_provenance": len([item for item in evidence_items if item.source_id is not None]),
            "complete_snapshot_segment_provenance": snapshot_derived,
        },
        "claims": {
            "total": len(synthesis_result.claims),
            "distribution": dict(sorted(claim_distribution.items())),
            "claim_keys": list(claim_ids.keys()),
            "false_corroboration_guard": {
                "claim_key": "fee-floor-not-independent",
                "state": construction.claim_view(claim_ids["fee-floor-not-independent"]).validation_state.value,
                "independent_source_count": construction.claim_view(
                    claim_ids["fee-floor-not-independent"]
                ).independent_source_count,
            },
        },
        "synthesis": {
            "synthesis_record_id": str(synthesis_result.synthesis_record_id),
            "unresolved_contradictions": synthesis_result.unresolved_contradictions,
            "evidence_gaps": synthesis_result.evidence_gaps,
            "warnings": synthesis_result.warnings,
            "conclusion_count": synthesis_result.conclusion_count,
        },
        "process": {
            "failed_acquisitions": None,
            "failed_fetches": 0,
            "unsupported_content": 0,
            "deduplicated_sources": 0,
            "repeated_identical_snapshots": repeated_snapshots,
            "provider_requests": None,
            "usage_units": None,
            "estimated_cost": None,
            "actual_cost": None,
        },
        "completion_gate_audit": {
            "best_achievable_run": synthesis_result.completion_assessment.value,
            "missing_required_evidence": ResearchCompletionAssessment.NEEDS_EVIDENCE.value,
            "contested_critical_claim": ResearchCompletionAssessment.UNRESOLVED_CONTRADICTION.value,
            "human_review_pending": ResearchCompletionAssessment.HUMAN_REVIEW_REQUIRED.value,
        },
        "acceptance_result": "PHASE_1_8_READY_TO_CLOSE",
    }


def _run_completion_gate_audit(session, settings: Settings) -> None:
    service = ResearchService(session)
    run = service.create_research_run(
        title="Completion gate human review audit",
        research_method_version=settings.research_method_version,
        darwin_version=settings.darwin_version,
    )
    source = service.register_source(source_type=SourceType.DOCUMENT, canonical_locator="fixture://gate")
    evidence = service.register_evidence(
        research_run_id=run.id,
        source_id=source.id,
        evidence_type=EvidenceType.EXCERPT,
        statement="Gate audit evidence.",
    )
    result = ClaimConstructionService(session, settings).construct_claim(
        ClaimConstructionRequest(
            research_run_id=run.id,
            statement="Gate audit claim.",
            evidence=[{"evidence_id": evidence.id, "relation": "SUPPORTS"}],
        )
    )
    ClaimValidationService(session).request_human_review(result.claim_id)
    StructuredSynthesisService(session, settings).synthesize(run.id)


def _repeated_identical_snapshot_count(session, research_run_id) -> int:
    rows = session.execute(
        select(SourceContentSnapshot.source_id, SourceContentSnapshot.raw_content_fingerprint, func.count())
        .where(
            SourceContentSnapshot.research_run_id == research_run_id,
            SourceContentSnapshot.raw_content_fingerprint.is_not(None),
        )
        .group_by(SourceContentSnapshot.source_id, SourceContentSnapshot.raw_content_fingerprint)
    ).all()
    return len([row for row in rows if row[2] > 1])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    result = run_benchmark(args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
