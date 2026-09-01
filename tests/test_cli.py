import json

from typer.testing import CliRunner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from darwin.cli.app import app
from darwin.config import get_settings
from darwin.db import Base
from darwin.db.models import (
    Claim,
    ClaimCandidateProposal,
    ClaimEvidence,
    ClaimEvidenceRelation,
    ClaimValidationEvaluation,
    ConclusionStatus,
    Evidence,
    EvidenceType,
    EvidenceCandidateProposal,
    ResearchCompletionAssessment,
    ResearchLoopEvent,
    ResearchLoopExecution,
    ResearchLoopExecutionMode,
    ResearchLoopState,
    ResearchLoopStopReason,
    ResearchPlanItem,
    ResearchPlanItemStatus,
    ResearchPlanPriority,
    ResearchPlanProposal,
    ResearchRun,
    SourceContentSegment,
    SourceContentSnapshot,
    SourceFetchStatus,
    SourceType,
)
from darwin.research import ResearchService


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Darwin Research & Intelligence Engine" in result.stdout


def test_cli_status(monkeypatch) -> None:
    monkeypatch.setenv("DARWIN_ENV", "test")
    get_settings.cache_clear()

    try:
        result = CliRunner().invoke(app, ["status"])
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0
    assert "Darwin status: ok" in result.stdout
    assert "Environment: test" in result.stdout


def test_research_cli_help() -> None:
    result = CliRunner().invoke(app, ["research", "--help"])

    assert result.exit_code == 0
    assert "Research run persistence smoke commands" in result.stdout
    assert "create-run" in result.stdout
    assert "get-run" in result.stdout
    assert "export-run" in result.stdout
    assert "list-runs" in result.stdout
    assert "validate-claim" in result.stdout
    assert "run-manual" in result.stdout
    assert "plan" in result.stdout
    assert "plan-show" in result.stdout
    assert "plan-approve" in result.stdout
    assert "propose-evidence" in result.stdout
    assert "evidence-candidates" in result.stdout
    assert "accept-evidence" in result.stdout
    assert "reject-evidence" in result.stdout
    assert "propose-claims" in result.stdout
    assert "claim-candidates" in result.stdout
    assert "accept-claim" in result.stdout
    assert "reject-claim" in result.stdout
    assert "acquire" in result.stdout
    assert "fetch-source" in result.stdout
    assert "source-content" in result.stdout
    assert "extract-evidence" in result.stdout
    assert "construct-claim" in result.stdout
    assert "claim" in result.stdout
    assert "synthesize" in result.stdout
    assert "loop-start" in result.stdout
    assert "loop-show" in result.stdout
    assert "loop-events" in result.stdout
    assert "loop-list" in result.stdout
    assert "loop-resume" in result.stdout


def test_research_loop_cli_dry_run_smoke(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'darwin-loop.sqlite'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    monkeypatch.setenv("DARWIN_DATABASE_URL", database_url)
    monkeypatch.setenv("DARWIN_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    get_settings.cache_clear()
    try:
        start_result = CliRunner().invoke(
            app,
            [
                "research",
                "loop-start",
                "Can the research loop dry run safely?",
                "--mode",
                "dry-run",
            ],
        )
        with session_factory() as session:
            execution = session.query(ResearchLoopExecution).one()
            execution_id = str(execution.id)
            assert session.query(ResearchLoopEvent).count() >= 3

        show_result = CliRunner().invoke(app, ["research", "loop-show", execution_id])
        events_result = CliRunner().invoke(app, ["research", "loop-events", execution_id])
    finally:
        get_settings.cache_clear()

    assert start_result.exit_code == 0
    assert "State: COMPLETED" in start_result.stdout
    assert "Stop reason: DRY_RUN_COMPLETE" in start_result.stdout
    assert "Completion: INCOMPLETE" in start_result.stdout
    assert show_result.exit_code == 0
    assert "State: COMPLETED" in show_result.stdout
    assert events_result.exit_code == 0
    assert "Events:" in events_result.stdout


def test_research_cli_lists_runs_with_status_filter(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'darwin-list-runs.sqlite'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        service = ResearchService(session)
        pending_run = service.create_research_run(
            title="CLI pending run",
            public_id="CLI-PENDING",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        hidden_run = service.create_research_run(
            title="CLI hidden run",
            public_id="CLI-HIDDEN",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        service.mark_started(hidden_run.id)
        service.mark_completed(hidden_run.id)
        source = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/cli-list-runs",
        )
        service.register_evidence(
            research_run_id=pending_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="CLI list-runs reports evidence counts.",
        )
        session.commit()

    monkeypatch.setenv("DARWIN_DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        result = CliRunner().invoke(
            app,
            ["research", "list-runs", "--status", "pending", "--limit", "1"],
        )
        invalid = CliRunner().invoke(app, ["research", "list-runs", "--status", "unknown"])
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0
    assert "Research runs: 1" in result.stdout
    assert "CLI-PENDING" in result.stdout
    assert "Status: PENDING" in result.stdout
    assert "Counts: sources=1, evidence=1, claims=0, conclusions=0" in result.stdout
    assert "CLI-HIDDEN" not in result.stdout
    assert invalid.exit_code == 1
    assert "Unsupported research run status" in invalid.stdout


def test_research_cli_exports_run_to_stdout_and_file(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'darwin-export-run.sqlite'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="CLI export run",
            public_id="CLI-EXPORT",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        source = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/cli-export",
        )
        evidence = service.register_evidence(
            research_run_id=research_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="CLI export includes evidence.",
        )
        claim = service.register_claim(
            research_run_id=research_run.id,
            statement="CLI export preserves claim links.",
        )
        service.link_claim_evidence(
            claim_id=claim.id,
            evidence_id=evidence.id,
            relation=ClaimEvidenceRelation.SUPPORTS,
        )
        service.register_conclusion(
            research_run_id=research_run.id,
            statement="CLI export includes conclusions.",
            status=ConclusionStatus.DRAFT,
        )
        session.commit()

    output_path = tmp_path / "export.json"
    monkeypatch.setenv("DARWIN_DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        stdout_result = CliRunner().invoke(app, ["research", "export-run", "CLI-EXPORT"])
        file_result = CliRunner().invoke(
            app,
            ["research", "export-run", "CLI-EXPORT", "--output", str(output_path)],
        )
        missing_result = CliRunner().invoke(app, ["research", "export-run", "MISSING"])
    finally:
        get_settings.cache_clear()

    assert stdout_result.exit_code == 0
    stdout_payload = json.loads(stdout_result.stdout)
    assert stdout_payload["schema_version"] == "research-record-export.v1"
    assert stdout_payload["research_run"]["public_id"] == "CLI-EXPORT"
    assert stdout_payload["summary"] == {
        "source_count": 1,
        "evidence_count": 1,
        "claim_count": 1,
        "claim_evidence_count": 1,
        "conclusion_count": 1,
    }
    assert file_result.exit_code == 0
    assert f"Research record export written: {output_path}" in file_result.stdout
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert file_payload["research_run"]["public_id"] == "CLI-EXPORT"
    assert missing_result.exit_code == 1
    assert "Research run not found: MISSING" in missing_result.stdout


def test_research_loop_cli_lists_executions_for_research_run(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'darwin-loop-list.sqlite'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        research_run = ResearchService(session).create_research_run(
            title="CLI loop list run",
            public_id="CLI-LOOP-LIST",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        execution = ResearchLoopExecution(
            research_run_id=research_run.id,
            execution_mode=ResearchLoopExecutionMode.DRY_RUN,
            state=ResearchLoopState.COMPLETED,
            current_stage=ResearchLoopState.COMPLETED.value,
            iteration_count=0,
            request_payload={"research_question": "CLI loop list?"},
            budget_payload={},
            counters={"iterations": 0, "searches": 0, "accepted_evidence": 0, "accepted_claims": 0},
            provider_payload={},
            stop_reason=ResearchLoopStopReason.DRY_RUN_COMPLETE,
            completion_assessment=ResearchCompletionAssessment.INCOMPLETE,
            loop_method_version="test",
        )
        session.add(execution)
        session.flush()
        session.add(
            ResearchLoopEvent(
                execution_id=execution.id,
                sequence=1,
                stage=ResearchLoopState.COMPLETED,
                event_type="DRY_RUN",
                status="OK",
                message="Dry run complete.",
                linked_object_ids={},
                counters={},
                warnings=[],
                errors=[],
            )
        )
        session.commit()

    monkeypatch.setenv("DARWIN_DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        result = CliRunner().invoke(
            app,
            ["research", "loop-list", "--research-run-id", "CLI-LOOP-LIST"],
        )
        missing = CliRunner().invoke(
            app,
            ["research", "loop-list", "--research-run-id", "MISSING-RUN"],
        )
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0
    assert "Loop executions: 1" in result.stdout
    assert f"Execution: {execution.id}" in result.stdout
    assert "Mode: DRY_RUN" in result.stdout
    assert "Latest event:" in result.stdout
    assert missing.exit_code == 1
    assert "Research loop list failed: Research run not found: MISSING-RUN" in missing.stdout


def test_research_acquire_cli_fake_provider(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'darwin.sqlite'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        research_run = ResearchService(session).create_research_run(
            title="CLI acquisition run",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        session.commit()
        research_run_id = str(research_run.id)

    monkeypatch.setenv("DARWIN_DATABASE_URL", database_url)
    monkeypatch.setenv("DARWIN_EXTERNAL_SEARCH_PROVIDER", "fake")
    get_settings.cache_clear()
    try:
        result = CliRunner().invoke(
            app,
            [
                "research",
                "acquire",
                "CLI source discovery",
                "--research-run-id",
                research_run_id,
                "--provider",
                "fake",
            ],
        )
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0
    assert "Status: SUCCESS" in result.stdout
    assert "Provider: fake" in result.stdout
    assert "Candidates discovered: 1" in result.stdout
    assert "Sources registered: 1" in result.stdout


def test_source_content_cli_help() -> None:
    runner = CliRunner()

    assert runner.invoke(app, ["research", "fetch-source", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "source-content", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "extract-evidence", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "construct-claim", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "claim", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "synthesize", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "plan", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "plan-show", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "plan-approve", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "propose-evidence", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "evidence-candidates", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "accept-evidence", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "reject-evidence", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "propose-claims", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "claim-candidates", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "accept-claim", "--help"]).exit_code == 0
    assert runner.invoke(app, ["research", "reject-claim", "--help"]).exit_code == 0


def test_research_planner_cli_plan_show_and_approve(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'darwin-planning.sqlite'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    monkeypatch.setenv("DARWIN_DATABASE_URL", database_url)
    monkeypatch.setenv("DARWIN_RESEARCH_PLANNING_PROVIDER", "fake")
    get_settings.cache_clear()
    try:
        plan_result = CliRunner().invoke(
            app,
            ["research", "plan", "How should planning work?", "--provider", "fake"],
        )
        with session_factory() as session:
            proposal_id = str(session.query(ResearchPlanProposal).one().id)
            assert session.query(ResearchRun).count() == 0

        show_result = CliRunner().invoke(app, ["research", "plan-show", proposal_id])
        approve_result = CliRunner().invoke(app, ["research", "plan-approve", proposal_id])
    finally:
        get_settings.cache_clear()

    assert plan_result.exit_code == 0
    assert "Approval status: PROPOSED" in plan_result.stdout
    assert "Provider: fake" in plan_result.stdout
    assert "Tasks: 2" in plan_result.stdout
    assert show_result.exit_code == 0
    assert "Proposal:" in show_result.stdout
    assert approve_result.exit_code == 0
    assert "Approval mode: MANUAL" in approve_result.stdout
    with session_factory() as session:
        assert session.query(ResearchRun).count() == 1


def test_source_content_cli_fake_fetch_and_extract(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'darwin-content.sqlite'}"
    artifact_root = tmp_path / "artifacts"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="CLI content run",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        source = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/content",
        )
        session.commit()
        research_run_id = str(research_run.id)
        source_id = str(source.id)

    monkeypatch.setenv("DARWIN_DATABASE_URL", database_url)
    monkeypatch.setenv("DARWIN_ARTIFACT_ROOT", str(artifact_root))
    get_settings.cache_clear()
    try:
        fetch_result = CliRunner().invoke(
            app,
            [
                "research",
                "fetch-source",
                source_id,
                "--research-run-id",
                research_run_id,
                "--fetcher",
                "fake",
            ],
        )
        with session_factory() as session:
            snapshot = session.query(SourceContentSnapshot).one()
            segment = session.query(SourceContentSegment).one()
            snapshot_id = str(snapshot.id)
            segment_id = str(segment.id)

        list_result = CliRunner().invoke(app, ["research", "source-content", snapshot_id])
        extract_result = CliRunner().invoke(
            app,
            [
                "research",
                "extract-evidence",
                segment_id,
                "--research-run-id",
                research_run_id,
            ],
        )
    finally:
        get_settings.cache_clear()

    assert fetch_result.exit_code == 0
    assert "Fetch status: SUCCESS" in fetch_result.stdout
    assert "Segments: 1" in fetch_result.stdout
    assert list_result.exit_code == 0
    assert "Segments: 1" in list_result.stdout
    assert extract_result.exit_code == 0
    assert "Extraction status: EXTRACTED" in extract_result.stdout
    with session_factory() as session:
        assert session.query(Evidence).count() == 1
        assert session.query(Claim).count() == 0


def test_assisted_extraction_cli_propose_list_accept(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'darwin-assisted.sqlite'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="CLI assisted extraction run",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        plan_item = ResearchPlanItem(
            research_run=research_run,
            item_key="cli-plan",
            requirement="Find an exact excerpt.",
            category="primary",
            priority=ResearchPlanPriority.HIGH,
            is_required=True,
            status=ResearchPlanItemStatus.PENDING,
            expected_source_type=SourceType.WEB_PAGE,
        )
        session.add(plan_item)
        source = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/assisted",
        )
        snapshot = SourceContentSnapshot(
            research_run=research_run,
            source=source,
            requested_locator=source.canonical_locator,
            final_locator=source.canonical_locator,
            fetch_status=SourceFetchStatus.SUCCESS,
            retrieval_method_version="fake",
            normalization_method_version="fake",
            segment_count=1,
        )
        session.add_all([plan_item, snapshot])
        session.flush()
        segment = SourceContentSegment(
            snapshot=snapshot,
            source=source,
            segment_identifier="seg-1",
            segment_order=0,
            text="Assisted extraction keeps candidates separate from Evidence.",
            locator="https://example.com/assisted#seg-1",
            char_start=0,
            char_end=58,
            line_start=1,
            line_end=1,
            fingerprint="cli-fingerprint",
        )
        session.add(segment)
        session.commit()
        ids = {
            "run": str(research_run.id),
            "plan": str(plan_item.id),
            "source": str(source.id),
            "snapshot": str(snapshot.id),
            "segment": str(segment.id),
        }

    monkeypatch.setenv("DARWIN_DATABASE_URL", database_url)
    monkeypatch.setenv("DARWIN_ASSISTED_EVIDENCE_EXTRACTION_PROVIDER", "fake")
    get_settings.cache_clear()
    try:
        propose_result = CliRunner().invoke(
            app,
            [
                "research",
                "propose-evidence",
                "--research-run-id",
                ids["run"],
                "--research-plan-item-id",
                ids["plan"],
                "--source-id",
                ids["source"],
                "--snapshot-id",
                ids["snapshot"],
                "--segment-id",
                ids["segment"],
                "--objective",
                "CLI objective",
                "--requirement",
                "CLI requirement",
                "--provider",
                "fake",
            ],
        )
        with session_factory() as session:
            candidate_id = str(session.query(EvidenceCandidateProposal).one().id)
            assert session.query(Evidence).count() == 0

        list_result = CliRunner().invoke(app, ["research", "evidence-candidates"])
        accept_result = CliRunner().invoke(app, ["research", "accept-evidence", candidate_id])
    finally:
        get_settings.cache_clear()

    assert propose_result.exit_code == 0
    assert "Candidates: 1" in propose_result.stdout
    assert "Status: VALIDATED" in propose_result.stdout
    assert list_result.exit_code == 0
    assert "Candidates: 1" in list_result.stdout
    assert accept_result.exit_code == 0
    assert "Status: ACCEPTED" in accept_result.stdout
    with session_factory() as session:
        assert session.query(Evidence).count() == 1
        assert session.query(Claim).count() == 0


def test_assisted_claim_cli_propose_list_accept(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'darwin-assisted-claims.sqlite'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        service = ResearchService(session)
        research_run = service.create_research_run(
            title="CLI assisted claim run",
            research_method_version="0.1.0",
            darwin_version="0.1.0",
        )
        plan_item = ResearchPlanItem(
            research_run=research_run,
            item_key="cli-claim-plan",
            requirement="Construct one claim.",
            category="claims",
            priority=ResearchPlanPriority.HIGH,
            is_required=True,
            status=ResearchPlanItemStatus.PENDING,
            expected_source_type=SourceType.WEB_PAGE,
        )
        session.add(plan_item)
        source = service.register_source(
            source_type=SourceType.WEB_PAGE,
            canonical_locator="https://example.com/assisted-claims",
        )
        evidence = service.register_evidence(
            research_run_id=research_run.id,
            source_id=source.id,
            evidence_type=EvidenceType.EXCERPT,
            statement="Assisted claim construction keeps candidates separate from Claims.",
            source_locator="https://example.com/assisted-claims#e1",
            metadata={"research_plan_item_id": str(plan_item.id)},
        )
        session.commit()
        ids = {
            "run": str(research_run.id),
            "plan": str(plan_item.id),
            "evidence": str(evidence.id),
        }

    monkeypatch.setenv("DARWIN_DATABASE_URL", database_url)
    monkeypatch.setenv("DARWIN_ASSISTED_CLAIM_CONSTRUCTION_PROVIDER", "fake")
    get_settings.cache_clear()
    try:
        propose_result = CliRunner().invoke(
            app,
            [
                "research",
                "propose-claims",
                "--research-run-id",
                ids["run"],
                "--research-plan-item-id",
                ids["plan"],
                "--evidence-id",
                ids["evidence"],
                "--objective",
                "CLI claim objective",
                "--instruction",
                "Create one bounded Claim candidate.",
                "--provider",
                "fake",
            ],
        )
        with session_factory() as session:
            candidate_id = str(session.query(ClaimCandidateProposal).one().id)
            assert session.query(Evidence).count() == 1
            assert session.query(Claim).count() == 0

        list_result = CliRunner().invoke(app, ["research", "claim-candidates"])
        accept_result = CliRunner().invoke(app, ["research", "accept-claim", candidate_id])
    finally:
        get_settings.cache_clear()

    assert propose_result.exit_code == 0
    assert "Candidates: 1" in propose_result.stdout
    assert "Status: VALIDATED" in propose_result.stdout
    assert list_result.exit_code == 0
    assert "Candidates: 1" in list_result.stdout
    assert accept_result.exit_code == 0
    assert "Status: ACCEPTED" in accept_result.stdout
    with session_factory() as session:
        assert session.query(Evidence).count() == 1
        assert session.query(Claim).count() == 1
        assert session.query(ClaimEvidence).count() == 1
        assert session.query(ClaimValidationEvaluation).count() == 0
