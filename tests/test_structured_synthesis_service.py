import json

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from typer.testing import CliRunner

from darwin.cli.app import app
from darwin.config import Settings, get_settings
from darwin.construction import ClaimConstructionRequest, ClaimConstructionService
from darwin.db import Base
from darwin.db.models import (
    ClaimValidationState,
    ConclusionClaim,
    ConclusionClaimRelation,
    EvidenceType,
    ResearchCompletionAssessment,
    ResearchSynthesisRecord,
    SourceType,
)
from darwin.research import ResearchService
from darwin.synthesis import ConclusionClaimLinkRequest, StructuredSynthesisService
from darwin.validation import ClaimValidationService


def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        env="test",
        database_url="sqlite+pysqlite:///:memory:",
        artifact_root=tmp_path / "artifacts",
        structured_synthesis_method_version="structured-synthesis-test",
    )


def create_claim(session, app_settings, *, statement, relation="SUPPORTS"):
    service = ResearchService(session)
    research_run = service.create_research_run(
        title="Synthesis test",
        research_method_version="research-method-test",
        darwin_version="0.1.0",
    )
    source = service.register_source(
        source_type=SourceType.DOCUMENT,
        canonical_locator=f"fixture://{statement}",
    )
    evidence = service.register_evidence(
        research_run_id=research_run.id,
        source_id=source.id,
        evidence_type=EvidenceType.EXCERPT,
        statement=f"Evidence for {statement}",
    )
    result = ClaimConstructionService(session, app_settings).construct_claim(
        ClaimConstructionRequest(
            research_run_id=research_run.id,
            statement=statement,
            evidence=[{"evidence_id": evidence.id, "relation": relation}],
        )
    )
    return research_run, result


def test_structured_synthesis_persists_append_only_claim_and_conclusion_trace(session_factory, tmp_path) -> None:
    app_settings = settings(tmp_path)
    with session_factory.begin() as session:
        research_run, result = create_claim(session, app_settings, statement="Traceable synthesis")
        conclusion = ResearchService(session).register_conclusion(
            research_run_id=research_run.id,
            statement="The conclusion depends on the explicit claim.",
        )
        synthesis = StructuredSynthesisService(session, app_settings)
        synthesis.link_conclusion_claim(
            ConclusionClaimLinkRequest(
                conclusion_id=conclusion.id,
                claim_id=result.claim_id,
                relation=ConclusionClaimRelation.SUPPORTS_CONCLUSION,
            )
        )
        first = synthesis.synthesize(research_run.id)
        second = synthesis.synthesize(research_run.id)

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ConclusionClaim)) == 1
        assert session.scalar(select(func.count()).select_from(ResearchSynthesisRecord)) == 2
    assert first.synthesis_record_id != second.synthesis_record_id
    assert first.claims[0].evidence[0].source_id is not None
    assert first.conclusions[0].claim_links[0].claim_id == result.claim_id
    assert first.synthesis_method_version == "structured-synthesis-test"


def test_synthesis_warns_for_contested_insufficient_and_human_review_claims(session_factory, tmp_path) -> None:
    app_settings = settings(tmp_path)
    with session_factory.begin() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="Warnings synthesis",
            research_method_version="research-method-test",
            darwin_version="0.1.0",
        )
        source = service.register_source(source_type=SourceType.DOCUMENT, canonical_locator="fixture://a")
        evidence_a = service.register_evidence(
            research_run_id=research_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="Support exists.",
        )
        evidence_b = service.register_evidence(
            research_run_id=research_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="Contradiction exists.",
        )
        construction = ClaimConstructionService(session, app_settings)
        contested = construction.construct_claim(
            ClaimConstructionRequest(
                research_run_id=research_run.id,
                statement="Contested claim",
                evidence=[
                    {"evidence_id": evidence_a.id, "relation": "SUPPORTS"},
                    {"evidence_id": evidence_b.id, "relation": "CONTRADICTS"},
                ],
            )
        )
        review = construction.construct_claim(
            ClaimConstructionRequest(
                research_run_id=research_run.id,
                statement="Review claim",
                evidence=[{"evidence_id": evidence_a.id, "relation": "CONTEXTUALIZES"}],
            )
        )
        ClaimValidationService(session).request_human_review(review.claim_id)
        conclusion = service.register_conclusion(
            research_run_id=research_run.id,
            statement="Conclusion remains conditional.",
        )
        synthesis = StructuredSynthesisService(session, app_settings)
        synthesis.link_conclusion_claim(
            ConclusionClaimLinkRequest(
                conclusion_id=conclusion.id,
                claim_id=contested.claim_id,
                relation=ConclusionClaimRelation.SUPPORTS_CONCLUSION,
            )
        )
        result = synthesis.synthesize(research_run.id)

    assert result.completion_assessment is ResearchCompletionAssessment.HUMAN_REVIEW_REQUIRED
    assert "claim_has_unresolved_contradiction" in result.warnings
    assert "claim_human_review_pending" in result.warnings
    assert "conclusion_claim_has_unresolved_contradiction" in result.warnings
    assert str(contested.claim_id) in result.unresolved_contradictions


def test_human_validated_claim_remains_distinct_from_independent_source_support(session_factory, tmp_path) -> None:
    app_settings = settings(tmp_path)
    with session_factory.begin() as session:
        research_run, result = create_claim(session, app_settings, statement="Human validated claim")
        ClaimValidationService(session).record_human_validation(result.claim_id)
        synthesis = StructuredSynthesisService(session, app_settings).synthesize(research_run.id)

    claim = synthesis.claims[0]
    assert claim.validation_state is ClaimValidationState.HUMAN_VALIDATED
    assert claim.independent_source_count == 1
    assert "claim_human_validated" in claim.warnings


def test_conclusion_claim_requires_same_research_run(session_factory, tmp_path) -> None:
    app_settings = settings(tmp_path)
    with session_factory.begin() as session:
        _run_a, result_a = create_claim(session, app_settings, statement="Claim A")
        run_b, _result_b = create_claim(session, app_settings, statement="Claim B")
        conclusion = ResearchService(session).register_conclusion(
            research_run_id=run_b.id,
            statement="Wrong run conclusion.",
        )
        try:
            StructuredSynthesisService(session, app_settings).link_conclusion_claim(
                ConclusionClaimLinkRequest(
                    conclusion_id=conclusion.id,
                    claim_id=result_a.claim_id,
                    relation=ConclusionClaimRelation.SUPPORTS_CONCLUSION,
                )
            )
        except Exception:
            pass

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ConclusionClaim)) == 0


def test_claim_construction_and_synthesis_cli_smoke(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "darwin-synthesis-cli.sqlite"
    database_url = f"sqlite+pysqlite:///{database_path}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory.begin() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="CLI synthesis",
            research_method_version="research-method-test",
            darwin_version="0.1.0",
        )
        source = service.register_source(source_type=SourceType.DOCUMENT, canonical_locator="fixture://cli")
        evidence = service.register_evidence(
            research_run_id=research_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="CLI evidence exists.",
        )
        research_run_id = str(research_run.id)
        evidence_id = str(evidence.id)

    input_file = tmp_path / "claim.json"
    input_file.write_text(
        json.dumps(
            {
                "research_run_id": research_run_id,
                "statement": "CLI constructs explicit claims.",
                "evidence": [{"evidence_id": evidence_id, "relation": "SUPPORTS"}],
            }
        )
    )
    monkeypatch.setenv("DARWIN_DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        construct = CliRunner().invoke(app, ["research", "construct-claim", str(input_file)])
        claim_id = json.loads(construct.stdout)["claim_id"]
        claim = CliRunner().invoke(app, ["research", "claim", claim_id])
        synthesis = CliRunner().invoke(app, ["research", "synthesize", research_run_id])
    finally:
        get_settings.cache_clear()

    assert construct.exit_code == 0
    assert claim.exit_code == 0
    assert "Validation state: SUPPORTED" in claim.stdout
    assert synthesis.exit_code == 0
    assert json.loads(synthesis.stdout)["claim_count"] == 1
