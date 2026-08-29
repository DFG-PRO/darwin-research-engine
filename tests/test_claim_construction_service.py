import json
import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import event, func, select
from sqlalchemy.orm import sessionmaker

from darwin.config import Settings
from darwin.construction import ClaimConstructionError, ClaimConstructionRequest, ClaimConstructionService
from darwin.db.models import (
    Claim,
    ClaimConstructionMethod,
    ClaimConstructionRecord,
    ClaimEvidenceRelation,
    ClaimValidationReasonCode,
    ClaimValidationState,
    Evidence,
    EvidenceType,
    SourceContentSegment,
    SourceContentSnapshot,
    SourceFetchStatus,
    SourceLineageType,
    SourceType,
)
from darwin.research import ResearchService


def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        env="test",
        database_url="sqlite+pysqlite:///:memory:",
        artifact_root=tmp_path / "artifacts",
        claim_statement_max_chars=120,
        claim_construction_method_version="manual-explicit-test",
    )


def create_run_source_evidence(session, *, locator="fixture://source-a"):
    service = ResearchService(session)
    research_run = service.create_research_run(
        title="Construction test",
        research_method_version="research-method-test",
        darwin_version="0.1.0",
    )
    source = service.register_source(
        source_type=SourceType.DOCUMENT,
        canonical_locator=locator,
        title="Fixture source",
    )
    evidence = service.register_evidence(
        research_run_id=research_run.id,
        source_id=source.id,
        evidence_type=EvidenceType.EXCERPT,
        statement="Explicit evidence is available.",
        source_locator="p1",
    )
    return research_run, source, evidence


def request_for(run_id, evidence_id, relation=ClaimEvidenceRelation.SUPPORTS):
    return ClaimConstructionRequest(
        research_run_id=run_id,
        statement="Darwin can construct explicit claims.",
        evidence=[{"evidence_id": evidence_id, "relation": relation}],
        metadata={"api_key": "do-not-store"},
    )


def test_construct_claim_persists_claim_links_audit_and_validation(session_factory, tmp_path) -> None:
    with session_factory.begin() as session:
        research_run, _source, evidence = create_run_source_evidence(session)
        result = ClaimConstructionService(session, settings(tmp_path)).construct_claim(
            request_for(research_run.id, evidence.id)
        )

    with session_factory() as session:
        record = session.get(ClaimConstructionRecord, result.construction_record_id)
        claim = session.get(Claim, result.claim_id)

        assert claim.statement == "Darwin can construct explicit claims."
        assert claim.evidence_links[0].relation is ClaimEvidenceRelation.SUPPORTS
        assert record.construction_method is ClaimConstructionMethod.MANUAL_EXPLICIT
        assert record.construction_method_version == "manual-explicit-test"
        assert record.construction_metadata["api_key"] == "[REDACTED]"
        assert len(record.evidence_selections) == 1
        assert result.validation_state is ClaimValidationState.SUPPORTED
        assert result.validation_reason_codes == [ClaimValidationReasonCode.SINGLE_SUPPORTING_SOURCE]


def test_content_evidence_provenance_is_validated_and_exposed(session_factory, tmp_path) -> None:
    with session_factory.begin() as session:
        research_run, source, evidence = create_run_source_evidence(session)
        snapshot = SourceContentSnapshot(
            research_run_id=research_run.id,
            source_id=source.id,
            requested_locator=source.canonical_locator,
            fetch_status=SourceFetchStatus.SUCCESS,
            retrieval_method_version="fixture-fetch",
        )
        session.add(snapshot)
        session.flush()
        segment = SourceContentSegment(
            snapshot_id=snapshot.id,
            source_id=source.id,
            segment_identifier="seg-0001",
            segment_order=0,
            text=evidence.statement,
            locator="fixture://source-a#seg-0001",
            char_start=0,
            char_end=len(evidence.statement),
            line_start=1,
            line_end=1,
            fingerprint="abc123",
        )
        session.add(segment)
        session.flush()
        evidence.evidence_metadata = {
            "content_snapshot_id": str(snapshot.id),
            "source_content_segment_id": str(segment.id),
        }
        result = ClaimConstructionService(session, settings(tmp_path)).construct_claim(
            request_for(research_run.id, evidence.id)
        )
        claim_id = result.claim_id

    with session_factory() as session:
        view = ClaimConstructionService(session, settings(tmp_path)).claim_view(claim_id)

    assert view.evidence[0].snapshot_id == snapshot.id
    assert view.evidence[0].segment_id == segment.id
    assert view.evidence[0].source_id == source.id


def test_invalid_evidence_is_rejected_without_creating_claim(session_factory, tmp_path) -> None:
    with session_factory.begin() as session:
        research_run, _source, _evidence = create_run_source_evidence(session)
        other_run, _other_source, other_evidence = create_run_source_evidence(
            session,
            locator="fixture://source-b",
        )
        assert other_run.id != research_run.id
        with pytest.raises(ClaimConstructionError):
            ClaimConstructionService(session, settings(tmp_path)).construct_claim(
                request_for(research_run.id, other_evidence.id)
            )

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Claim)) == 0


def test_claim_statement_is_caller_supplied_and_bounded(session_factory, tmp_path) -> None:
    with pytest.raises(ValidationError):
        ClaimConstructionRequest(
            research_run_id=uuid.uuid4(),
            statement="",
            evidence=[{"evidence_id": uuid.uuid4(), "relation": "SUPPORTS"}],
        )

    with session_factory.begin() as session:
        research_run, _source, evidence = create_run_source_evidence(session)
        with pytest.raises(ClaimConstructionError):
            ClaimConstructionService(session, settings(tmp_path)).construct_claim(
                ClaimConstructionRequest(
                    research_run_id=research_run.id,
                    statement="x" * 121,
                    evidence=[{"evidence_id": evidence.id, "relation": "SUPPORTS"}],
                )
            )


def test_validation_states_and_source_independence_are_preserved(session_factory, tmp_path) -> None:
    with session_factory.begin() as session:
        service = ResearchService(session)
        research_run, origin, evidence_a = create_run_source_evidence(session)
        derived = service.register_source(
            source_type=SourceType.DOCUMENT,
            canonical_locator="fixture://derived",
            origin_source_id=origin.id,
            source_lineage_type=SourceLineageType.REPUBLISHED_FROM,
        )
        evidence_b = service.register_evidence(
            research_run_id=research_run.id,
            source_id=derived.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="Republished evidence repeats the same support.",
        )
        evidence_c = service.register_evidence(
            research_run_id=research_run.id,
            source_id=origin.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="Contradictory evidence is available.",
        )
        construction = ClaimConstructionService(session, settings(tmp_path))
        result = construction.construct_claim(
            ClaimConstructionRequest(
                research_run_id=research_run.id,
                statement="A claim cannot be inflated by republished evidence.",
                evidence=[
                    {"evidence_id": evidence_a.id, "relation": "SUPPORTS"},
                    {"evidence_id": evidence_b.id, "relation": "SUPPORTS"},
                ],
            )
        )
        contested = construction.construct_claim(
            ClaimConstructionRequest(
                research_run_id=research_run.id,
                statement="A contested claim preserves both sides.",
                evidence=[
                    {"evidence_id": evidence_a.id, "relation": "SUPPORTS"},
                    {"evidence_id": evidence_c.id, "relation": "CONTRADICTS"},
                ],
            )
        )
        contextual = construction.construct_claim(
            ClaimConstructionRequest(
                research_run_id=research_run.id,
                statement="Context alone does not establish support.",
                evidence=[{"evidence_id": evidence_a.id, "relation": "CONTEXTUALIZES"}],
            )
        )
        derived_view = construction.claim_view(result.claim_id)

    assert result.validation_state is ClaimValidationState.SUPPORTED
    assert derived_view.independent_source_count == 1
    assert contested.validation_state is ClaimValidationState.CONTESTED
    assert contextual.validation_state is ClaimValidationState.INSUFFICIENT_EVIDENCE


def test_failed_audit_insert_rolls_back_constructed_claim(session_factory, tmp_path) -> None:
    def fail_insert(*_args, **_kwargs):
        raise RuntimeError("forced audit failure")

    event.listen(ClaimConstructionRecord, "before_insert", fail_insert)
    try:
        with pytest.raises(RuntimeError):
            with session_factory.begin() as session:
                research_run, _source, evidence = create_run_source_evidence(session)
                ClaimConstructionService(session, settings(tmp_path)).construct_claim(
                    request_for(research_run.id, evidence.id)
                )
    finally:
        event.remove(ClaimConstructionRecord, "before_insert", fail_insert)

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Claim)) == 0
        assert session.scalar(select(func.count()).select_from(ClaimConstructionRecord)) == 0


def test_cli_input_contract_accepts_claim_statement_alias() -> None:
    payload = {
        "research_run_id": str(uuid.uuid4()),
        "claim_statement": "Alias is accepted for explicit claim statement.",
        "evidence": [{"evidence_id": str(uuid.uuid4()), "relation": "SUPPORTS"}],
    }

    request = ClaimConstructionRequest.model_validate_json(json.dumps(payload))

    assert request.statement == "Alias is accepted for explicit claim statement."
