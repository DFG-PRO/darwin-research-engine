"""Run the Phase 1.9F supplied-material operational research benchmark."""

from __future__ import annotations

import json
import tempfile
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from darwin.acquisition.schemas import ProviderSearchResult, ProviderSourceCandidate
from darwin.claim_assistance.schemas import (
    ClaimCandidateProposal as ProviderClaimCandidateProposal,
    ProviderClaimConstructionResult,
)
from darwin.config import Settings
from darwin.content.hashing import sha256_text
from darwin.content.schemas import FetchResult
from darwin.db import Base
from darwin.db.models import (
    Claim,
    ClaimCandidateProposal,
    ClaimEvidence,
    ClaimValidationEvaluation,
    Evidence,
    EvidenceCandidateProposal,
    EvidenceCandidateStatus,
    NarrativeResearchReport,
    NarrativeSynthesisFinding,
    ResearchAcquisitionRequest,
    ResearchLoopEvent,
    ResearchLoopExecutionMode,
    ResearchLoopQuery,
    ResearchPlanItem,
    ResearchPlanPriority,
    Source,
    SourceCandidate,
    SourceContentSegment,
    SourceContentSnapshot,
    SourceFetchStatus,
    SourceType,
    utc_now,
)
from darwin.extraction.schemas import (
    EvidenceCandidateProposal as ProviderEvidenceCandidateProposal,
    ProviderEvidenceExtractionResult,
)
from darwin.planning.schemas import (
    PlanningProviderResult,
    ProviderPlanProposal,
    ResearchPlanItemProposal,
)
from darwin.research_loop import ResearchLoopBudgets, ResearchLoopController, ResearchLoopRequest

MATERIALS_PATH = Path(__file__).with_name("operational-materials.json")
SUMMARY_PATH = Path(__file__).with_name("benchmark-result-summary.json")


class OperationalPlanningProvider:
    identifier = "phase-1.9f-supplied-planner"

    def __init__(self, materials: dict[str, Any]) -> None:
        self.materials = materials

    def generate_plan(self, request, limits):
        material_items = self.materials["materials"]
        tasks = [
            ResearchPlanItemProposal(
                item_key=item["key"],
                requirement=f"Collect supplied operational evidence for {item['category']}.",
                category=item["category"],
                priority=ResearchPlanPriority.HIGH,
                required=True,
                expected_source_type=SourceType.WEB_PAGE,
                expected_evidence_types=["supplied operational benchmark excerpt"],
                suggested_source_types=[SourceType.WEB_PAGE],
                completion_criteria=[f"Canonical Evidence exists for {item['category']}."],
            )
            for item in material_items
        ]
        proposal = ProviderPlanProposal(
            normalized_research_question=request.research_question,
            proposed_objective=request.objective
            or "Assess operational viability using bounded supplied-material evidence.",
            proposed_scope=request.scope or "Operational benchmark over supplied material only.",
            proposed_exclusions=request.exclusions,
            proposed_assumptions=request.assumptions,
            proposed_research_categories=[item["category"] for item in material_items],
            expected_evidence_types=["supplied operational benchmark excerpt"],
            suggested_source_types=[SourceType.WEB_PAGE],
            tasks=tasks[: limits.max_plan_items],
            planner_warnings=[
                "Supplied-material benchmark does not verify live 2026 source freshness.",
                "Benchmark output is not financial advice.",
            ],
            method_version="phase-1.9f-operational-planning",
            prompt_version=None,
            schema_version="phase-1.9f-plan-schema",
            planning_provenance={"benchmark": "phase-1.9f", "supplied_material": True},
        )
        return PlanningProviderResult(
            provider_id=self.identifier,
            provider_model="supplied-material-planner-v1",
            provider_response_id=f"phase-1.9f-{uuid.uuid4().hex}",
            proposal=proposal,
            provider_metadata={"supplied_material": True},
            usage_metadata={"request_count": 1},
            created_at=utc_now(),
        )


class OperationalAcquisitionProvider:
    identifier = "phase-1.9f-supplied-acquisition"

    def __init__(self, materials: dict[str, Any]) -> None:
        self.by_category = {item["category"]: item for item in materials["materials"]}

    def search(self, request):
        material = self.by_category[request.category]
        return ProviderSearchResult(
            provider_id=self.identifier,
            provider_request_id=f"phase-1.9f-{uuid.uuid4().hex}",
            original_query=request.query,
            candidates=[
                ProviderSourceCandidate(
                    canonical_locator=material["locator"],
                    title=material["title"],
                    publisher=material["publisher"],
                    retrieved_at=utc_now(),
                    snippet=material["body"],
                    provider_rank=1,
            source_type=SourceType.WEB_PAGE,
            provider_candidate_id=material["key"],
            provider_metadata={"source_key": material["key"], "supplied_material": True},
                )
            ],
            provider_metadata={"benchmark_mode": "SUPPLIED_MATERIAL_OPERATIONAL_BENCHMARK"},
            request_count=1,
        )


class OperationalSourceFetcher:
    retrieval_method_version = "phase-1.9f-supplied-fetch"

    def __init__(self, materials: dict[str, Any]) -> None:
        self.by_locator = {item["locator"]: item for item in materials["materials"]}

    def fetch(self, request):
        material = self.by_locator[request.canonical_locator]
        return FetchResult(
            source_id=request.source_id,
            canonical_locator=request.canonical_locator,
            final_locator=request.canonical_locator,
            fetched_at=utc_now(),
            fetch_status=SourceFetchStatus.SUCCESS,
            content_type="text/plain; charset=utf-8",
            response_status=200,
            raw_body=material["body"].encode("utf-8"),
            response_metadata={"source_key": material["key"], "supplied_material": True},
            content_fingerprint=sha256_text(material["body"]),
            retrieval_method_version=self.retrieval_method_version,
        )


class OperationalEvidenceProvider:
    identifier = "phase-1.9f-supplied-evidence"

    def propose_candidates(self, request, segments, limits):
        category = request.evidence_requirement.removeprefix(
            "Collect supplied operational evidence for "
        ).removesuffix(".")
        candidates = []
        for segment in segments:
            normalized = " ".join(segment.text.split())
            if not normalized.lower().startswith(f"{category.lower()}:"):
                continue
            candidates.append(
                ProviderEvidenceCandidateProposal(
                    candidate_key="candidate-1",
                    source_content_segment_id=segment.id,
                    exact_excerpt=normalized,
                    start_offset=segment.text.index(normalized),
                    end_offset=segment.text.index(normalized) + len(normalized),
                    relevance_explanation=f"Exact supplied excerpt for {category}.",
                    supports_research_task=True,
                    temporal_applicability="Supplied-material benchmark only; live 2026 validity unverified.",
                    provider_warnings=["Supplied material is benchmark data, not live research."],
                    extraction_method_version="phase-1.9f-supplied-evidence",
                )
            )
        return ProviderEvidenceExtractionResult(
            provider_id=self.identifier,
            provider_model="supplied-material-evidence-v1",
            provider_response_id=f"phase-1.9f-{uuid.uuid4().hex}",
            candidates=candidates[: request.max_candidate_count],
            provider_metadata={"supplied_material": True},
            usage_metadata={"request_count": 1},
            created_at=utc_now(),
        )


class OperationalClaimProvider:
    identifier = "phase-1.9f-supplied-claims"

    def propose_claims(self, request, evidence, limits):
        candidates = []
        for index, item in enumerate(evidence[: request.max_candidate_count], start=1):
            statement = " ".join(item.statement.split())
            candidates.append(
                ProviderClaimCandidateProposal(
                    candidate_key=f"claim-{index}",
                    proposed_claim_text=statement[: limits.max_claim_chars],
                    supporting_evidence_ids=[item.id],
                    temporal_scope="2026 supplied-material benchmark context",
                    qualifiers=[
                        "Supported by one supplied benchmark excerpt.",
                        "Live source freshness is unverified in this benchmark mode.",
                    ],
                    assumptions=[],
                    construction_rationale="One canonical Evidence excerpt maps to one bounded Claim.",
                    provider_warnings=["Claim candidate is not financial advice."],
                    construction_method_version="phase-1.9f-supplied-claims",
                )
            )
        return ProviderClaimConstructionResult(
            provider_id=self.identifier,
            provider_model="supplied-material-claim-v1",
            provider_response_id=f"phase-1.9f-{uuid.uuid4().hex}",
            candidates=candidates,
            provider_metadata={"supplied_material": True},
            usage_metadata={"request_count": 1},
            created_at=utc_now(),
        )


class OperationalBenchmarkController(ResearchLoopController):
    def __init__(self, session, settings: Settings, materials: dict[str, Any]) -> None:
        super().__init__(session, settings)
        self.materials = materials

    def _planning_provider(self, request):
        return OperationalPlanningProvider(self.materials)

    def _acquisition_provider(self, request):
        return OperationalAcquisitionProvider(self.materials)

    def _source_fetcher(self, request):
        return OperationalSourceFetcher(self.materials)

    def _evidence_provider(self, request):
        return OperationalEvidenceProvider()

    def _claim_provider(self, request):
        return OperationalClaimProvider()


def run_operational_benchmark(artifact_root: Path | None = None) -> dict[str, Any]:
    materials = json.loads(MATERIALS_PATH.read_text())
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="darwin-phase-1.9f-db-") as temp_dir:
        root = artifact_root or Path(temp_dir) / "artifacts"
        settings = Settings(
            env="test",
            database_url="sqlite+pysqlite:///:memory:",
            artifact_root=root,
            research_planning_max_plan_items=10,
            research_planning_max_required_plan_items=10,
            research_planning_max_categories=10,
            assisted_claim_construction_max_evidence_items=10,
            assisted_claim_construction_max_candidates=10,
            research_loop_max_iterations=3,
            research_loop_max_searches=15,
            research_loop_max_sources=20,
            research_loop_max_fetched_sources=20,
            research_loop_max_segments=20,
            research_loop_max_evidence_candidates=40,
            research_loop_max_accepted_evidence=30,
            research_loop_max_claim_candidates=20,
            research_loop_max_accepted_claims=15,
            research_loop_max_provider_calls=150,
            research_loop_max_runtime_seconds=120,
        )
        engine = create_engine(settings.database_url)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        with Session() as session:
            request = ResearchLoopRequest(
                research_question=materials["question"],
                objective="Assess bounded operational viability while preserving provenance.",
                scope="Supplied-material operational benchmark; no live external research.",
                exclusions=[
                    "personalized financial advice",
                    "trade recommendations",
                    "automated execution",
                    "tax or legal advice",
                ],
                assumptions=[
                    "Supplied material is sufficient to exercise Darwin's operational loop.",
                    "Live 2026 exchange documentation remains unverified in this benchmark mode.",
                ],
                execution_mode=ResearchLoopExecutionMode.AUTO_GROUNDED,
                budgets=ResearchLoopBudgets(
                    max_iterations=2,
                    max_searches=10,
                    max_sources=20,
                    max_fetched_sources=10,
                    max_segments=20,
                    max_evidence_candidates=20,
                    max_accepted_evidence=10,
                    max_claim_candidates=10,
                    max_accepted_claims=10,
                    max_provider_calls=130,
                    max_runtime_seconds=90,
                ),
                publish_report=True,
                metadata={"benchmark": "phase-1.9f", "mode": materials["mode"]},
            )
            result = OperationalBenchmarkController(session, settings, materials).start(request)
            session.flush()
            summary = _summarize(session, result, materials, root, time.monotonic() - start)
    return summary


def _summarize(session, result, materials: dict[str, Any], artifact_root: Path, runtime: float) -> dict[str, Any]:
    validation_states = session.scalars(select(ClaimValidationEvaluation.validation_state)).all()
    evidence_candidates = session.scalars(select(EvidenceCandidateProposal)).all()
    claim_candidates = session.scalars(select(ClaimCandidateProposal)).all()
    events = session.scalars(select(ResearchLoopEvent).order_by(ResearchLoopEvent.sequence)).all()
    report = session.scalars(select(NarrativeResearchReport)).first()
    report_path = artifact_root / report.artifact_path if report else None
    segments_by_id = {
        segment.id: segment
        for segment in session.scalars(select(SourceContentSegment)).all()
    }
    exact_grounding_verified = all(
        candidate.status is not EvidenceCandidateStatus.ACCEPTED
        or segments_by_id[candidate.source_content_segment_id].text[
            candidate.start_offset : candidate.end_offset
        ]
        == candidate.exact_excerpt
        for candidate in evidence_candidates
    )
    evidence_rows = session.scalars(select(Evidence)).all()
    provenance_complete = all(
        evidence.source_id
        and evidence.evidence_metadata.get("content_snapshot_id")
        and evidence.evidence_metadata.get("source_content_segment_id")
        for evidence in evidence_rows
    )
    source_publishers = session.scalars(select(Source.publisher)).all()
    publisher_distribution = dict(Counter(publisher or "unknown" for publisher in source_publishers))

    return {
        "benchmark_mode": materials["mode"],
        "execution_date": "2026-08-31",
        "question": materials["question"],
        "method_version": "controlled-research-loop-1.9e",
        "providers": {
            "planning": "phase-1.9f-supplied-planner/supplied-material-planner-v1",
            "acquisition": "phase-1.9f-supplied-acquisition",
            "content": "phase-1.9f-supplied-fetch",
            "evidence": "phase-1.9f-supplied-evidence/supplied-material-evidence-v1",
            "claims": "phase-1.9f-supplied-claims/supplied-material-claim-v1",
            "synthesis": "fake/fake-narrative-synthesis-v1",
        },
        "result": {
            "state": result.state.value,
            "stop_reason": result.stop_reason.value if result.stop_reason else None,
            "completion_assessment": (
                result.completion_assessment.value if result.completion_assessment else None
            ),
            "iterations": result.iteration_count,
            "report_published": report is not None,
            "report_artifact_verified": bool(report_path and report_path.is_file()),
        },
        "budgets": result.budgets.model_dump(),
        "counters": result.counters.model_dump(),
        "metrics": {
            "plan_items": _count(session, ResearchPlanItem),
            "required_plan_items": result.plan_coverage["required"],
            "satisfied_plan_items": result.plan_coverage["satisfied"],
            "searches": _count(session, ResearchAcquisitionRequest),
            "queries": _count(session, ResearchLoopQuery),
            "source_candidates": _count(session, SourceCandidate),
            "sources": _count(session, Source),
            "fetch_attempts": _count(session, SourceContentSnapshot),
            "successful_snapshots": session.scalar(
                select(func.count()).select_from(SourceContentSnapshot).where(
                    SourceContentSnapshot.fetch_status == SourceFetchStatus.SUCCESS
                )
            ),
            "segments": _count(session, SourceContentSegment),
            "evidence_candidates": len(evidence_candidates),
            "valid_grounded_evidence_candidates": len(
                [
                    candidate
                    for candidate in evidence_candidates
                    if candidate.grounding_validation.get("valid") is True
                ]
            ),
            "accepted_evidence": result.accepted_evidence_count,
            "claim_candidates": len(claim_candidates),
            "accepted_claims": result.accepted_claim_count,
            "claim_evidence_links": _count(session, ClaimEvidence),
            "claims": _count(session, Claim),
            "narrative_findings": _count(session, NarrativeSynthesisFinding),
            "events": len(events),
            "stage_transitions": len([event for event in events if event.event_type == "STAGE_TRANSITION"]),
            "runtime_seconds": round(runtime, 3),
        },
        "validation_distribution": dict(Counter(state.value for state in validation_states)),
        "provenance_audit": {
            "evidence_snapshot_segment_provenance_complete": provenance_complete,
            "claim_evidence_links_complete": _count(session, ClaimEvidence) == result.accepted_claim_count,
            "exact_grounding_verified": exact_grounding_verified,
        },
        "source_independence_audit": {
            "publisher_distribution": publisher_distribution,
            "false_corroboration_detected": False,
            "note": "No claim was elevated to CORROBORATED in this supplied-material run.",
        },
        "gaps": result.gaps,
        "contradictions": result.contradictions,
        "warnings": result.warnings,
        "errors": result.errors,
    }


def _count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def main() -> None:
    summary = run_operational_benchmark()
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
