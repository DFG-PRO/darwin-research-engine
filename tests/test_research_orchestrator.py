import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from typer.testing import CliRunner

from darwin.cli.app import app
from darwin.config import Settings, get_settings
from darwin.db import Base
from darwin.db.models import (
    Claim,
    ClaimValidationEvaluation,
    ClaimValidationState,
    Evidence,
    ResearchCompletionAssessment,
    ResearchFraming,
    ResearchPlanItem,
    ResearchRun,
    ResearchRunStatus,
    ResearchSynthesisRecord,
)
from darwin.orchestration import ManualResearchInput, ResearchOrchestrationError, ResearchOrchestrator


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def settings() -> Settings:
    return Settings(
        env="test",
        database_url="sqlite+pysqlite:///:memory:",
        research_method_version="research-method-v0.1-test",
    )


def complete_input() -> ManualResearchInput:
    return ManualResearchInput.model_validate(
        {
            "research_question": "Can Darwin run supplied research?",
            "framing": {
                "objective": "Evaluate supplied research material.",
                "scope": "Fixture input only.",
                "assumptions": ["All material is caller supplied."],
                "required_evidence_categories": ["primary"],
                "completion_criteria": ["Required evidence is supplied."],
            },
            "plan_items": [
                {
                    "item_key": "primary-evidence",
                    "requirement": "Provide primary evidence.",
                    "category": "primary",
                    "priority": "HIGH",
                    "required": True,
                }
            ],
            "sources": [
                {
                    "source_key": "source-a",
                    "source_type": "DOCUMENT",
                    "canonical_locator": "fixture://source-a",
                }
            ],
            "evidence": [
                {
                    "evidence_key": "evidence-a",
                    "source_key": "source-a",
                    "evidence_type": "EXCERPT",
                    "statement": "Supplied evidence exists.",
                    "plan_item_keys": ["primary-evidence"],
                }
            ],
            "claims": [
                {
                    "claim_key": "claim-a",
                    "statement": "Darwin can run supplied research.",
                    "evidence": [{"evidence_key": "evidence-a", "relation": "SUPPORTS"}],
                }
            ],
            "conclusions": [
                {"statement": "The supplied research workflow is structurally complete."}
            ],
        }
    )


def run_orchestrator(session_factory, manual_input: ManualResearchInput):
    with session_factory.begin() as session:
        return ResearchOrchestrator(session, settings()).run_manual(manual_input)


def test_happy_path_creates_complete_auditable_research_run(session_factory) -> None:
    result = run_orchestrator(session_factory, complete_input())

    assert result.completion_assessment is ResearchCompletionAssessment.COMPLETE
    assert result.run_status is ResearchRunStatus.COMPLETED
    assert result.source_count == 1
    assert result.evidence_count == 1
    assert result.claim_results[0].validation_state is ClaimValidationState.SUPPORTED
    assert result.conclusions[0].statement.startswith("The supplied research workflow")

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ResearchFraming)) == 1
        assert session.scalar(select(func.count()).select_from(ResearchPlanItem)) == 1
        assert session.scalar(select(func.count()).select_from(ResearchSynthesisRecord)) == 1


def test_corroborated_claim_uses_independent_sources(session_factory) -> None:
    data = complete_input().model_dump(mode="json")
    data["sources"].append(
        {
            "source_key": "source-b",
            "source_type": "DOCUMENT",
            "canonical_locator": "fixture://source-b",
        }
    )
    data["evidence"].append(
        {
            "evidence_key": "evidence-b",
            "source_key": "source-b",
            "evidence_type": "EXCERPT",
            "statement": "Independent supplied evidence exists.",
            "plan_item_keys": ["primary-evidence"],
        }
    )
    data["claims"][0]["evidence"].append({"evidence_key": "evidence-b", "relation": "SUPPORTS"})

    result = run_orchestrator(session_factory, ManualResearchInput.model_validate(data))

    assert result.claim_results[0].validation_state is ClaimValidationState.CORROBORATED
    assert result.completion_assessment is ResearchCompletionAssessment.COMPLETE


def test_contested_claim_remains_visible_in_synthesis(session_factory) -> None:
    data = complete_input().model_dump(mode="json")
    data["sources"].append(
        {
            "source_key": "source-b",
            "source_type": "DOCUMENT",
            "canonical_locator": "fixture://source-b",
        }
    )
    data["evidence"].append(
        {
            "evidence_key": "evidence-b",
            "source_key": "source-b",
            "evidence_type": "EXCERPT",
            "statement": "Contradictory supplied evidence exists.",
        }
    )
    data["claims"][0]["evidence"].append({"evidence_key": "evidence-b", "relation": "CONTRADICTS"})

    result = run_orchestrator(session_factory, ManualResearchInput.model_validate(data))

    assert result.claim_results[0].validation_state is ClaimValidationState.CONTESTED
    assert result.completion_assessment is ResearchCompletionAssessment.UNRESOLVED_CONTRADICTION
    assert result.unresolved_contradictions == ["claim-a"]
    assert result.run_status is ResearchRunStatus.IN_PROGRESS


def test_missing_required_plan_evidence_prevents_clean_completion(session_factory) -> None:
    data = complete_input().model_dump(mode="json")
    data["evidence"][0]["plan_item_keys"] = []

    result = run_orchestrator(session_factory, ManualResearchInput.model_validate(data))

    assert result.completion_assessment is ResearchCompletionAssessment.NEEDS_EVIDENCE
    assert result.evidence_gaps == ["primary-evidence"]
    assert result.run_status is ResearchRunStatus.IN_PROGRESS


def test_human_review_propagates_to_completion_assessment(session_factory) -> None:
    data = complete_input().model_dump(mode="json")
    data["human_review_claim_keys"] = ["claim-a"]

    result = run_orchestrator(session_factory, ManualResearchInput.model_validate(data))

    assert result.claim_results[0].validation_state is ClaimValidationState.HUMAN_REVIEW_PENDING
    assert result.completion_assessment is ResearchCompletionAssessment.HUMAN_REVIEW_REQUIRED
    assert "human_review_required" in result.warnings


def test_result_preserves_provenance_without_inventing_data(session_factory) -> None:
    result = run_orchestrator(session_factory, complete_input())

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Evidence)) == 1
        assert session.scalar(select(func.count()).select_from(Claim)) == 1
        assert session.scalar(select(func.count()).select_from(ClaimValidationEvaluation)) == 1

    assert result.source_count == 1
    assert result.evidence_count == 1
    assert len(result.claim_results) == 1


def test_failure_rolls_back_invalid_manual_research(session_factory) -> None:
    data = complete_input().model_dump(mode="json")
    data["claims"][0]["evidence"][0]["evidence_key"] = "missing-evidence"

    with pytest.raises(ResearchOrchestrationError):
        with session_factory.begin() as session:
            ResearchOrchestrator(session, settings()).run_manual(
                ManualResearchInput.model_validate(data)
            )

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ResearchRun)) == 0


def test_method_version_and_history_are_preserved(session_factory) -> None:
    result = run_orchestrator(session_factory, complete_input())

    assert result.research_method_version == "research-method-v0.1-test"

    with session_factory() as session:
        run = session.get(ResearchRun, result.research_run_id)
        synthesis = session.get(ResearchSynthesisRecord, result.synthesis_record_id)

        assert run.research_method_version == "research-method-v0.1-test"
        assert synthesis.research_method_version == "research-method-v0.1-test"


def test_cli_manual_research_fixture_executes_successfully(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "darwin-cli.sqlite"
    engine = create_engine(f"sqlite+pysqlite:///{database_path}")
    Base.metadata.create_all(engine)
    monkeypatch.setenv("DARWIN_ENV", "test")
    monkeypatch.setenv("DARWIN_DATABASE_URL", f"sqlite+pysqlite:///{database_path}")
    monkeypatch.setenv("DARWIN_RESEARCH_METHOD_VERSION", "research-method-v0.1-test")
    get_settings.cache_clear()

    fixture = Path("tests/fixtures/manual_research_complete.json")
    result = CliRunner().invoke(app, ["research", "run-manual", str(fixture)])

    get_settings.cache_clear()
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["completion_assessment"] == "COMPLETE"
    assert payload["research_method_version"] == "research-method-v0.1-test"


def test_cli_manual_research_malformed_input_fails(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "darwin-cli.sqlite"
    bad_input = tmp_path / "bad.json"
    bad_input.write_text('{"sources": []}')
    monkeypatch.setenv("DARWIN_ENV", "test")
    monkeypatch.setenv("DARWIN_DATABASE_URL", f"sqlite+pysqlite:///{database_path}")
    get_settings.cache_clear()

    result = CliRunner().invoke(app, ["research", "run-manual", str(bad_input)])

    get_settings.cache_clear()
    assert result.exit_code == 1
    assert "Manual research input failed" in result.stdout
