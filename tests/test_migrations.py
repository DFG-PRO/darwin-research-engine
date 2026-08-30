from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_script_directory_loads_revision() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    assert script.get_current_head() == "0008_assisted_evidence_extraction"


def test_alembic_offline_upgrade_compiles(capsys) -> None:
    config = Config("alembic.ini")

    command.upgrade(config, "head", sql=True)

    captured = capsys.readouterr()
    assert "CREATE TABLE research_runs" in captured.out
    assert "CREATE TABLE evidence" in captured.out
    assert "CREATE TABLE claim_evidence" in captured.out
    assert "CREATE TABLE claim_validation_evaluations" in captured.out
    assert "CREATE TABLE claim_human_validations" in captured.out
    assert "CREATE TABLE research_framings" in captured.out
    assert "CREATE TABLE research_plan_items" in captured.out
    assert "CREATE TABLE research_synthesis_records" in captured.out
    assert "CREATE TABLE research_acquisition_requests" in captured.out
    assert "CREATE TABLE source_candidates" in captured.out
    assert "CREATE TABLE source_content_snapshots" in captured.out
    assert "CREATE TABLE source_content_segments" in captured.out
    assert "CREATE TABLE evidence_extraction_records" in captured.out
    assert "CREATE TABLE claim_construction_records" in captured.out
    assert "CREATE TABLE claim_construction_evidence" in captured.out
    assert "CREATE TABLE conclusion_claims" in captured.out
    assert "CREATE TABLE research_plan_proposals" in captured.out
    assert "CREATE TABLE research_plan_proposal_items" in captured.out
    assert "CREATE TABLE assisted_evidence_extraction_requests" in captured.out
    assert "CREATE TABLE evidence_candidate_proposals" in captured.out
    assert "COMMIT;" in captured.out


def test_alembic_offline_downgrade_acquisition_revision_compiles(capsys) -> None:
    config = Config("alembic.ini")

    command.downgrade(
        config,
        "0004_external_research_acquisition:0003_research_method_orchestration",
        sql=True,
    )

    captured = capsys.readouterr()
    assert "DROP TABLE source_candidates" in captured.out
    assert "DROP TABLE research_acquisition_requests" in captured.out


def test_alembic_offline_downgrade_new_revision_compiles(capsys) -> None:
    config = Config("alembic.ini")

    command.downgrade(
        config,
        "0006_claim_construction_synthesis:0005_source_content_acquisition",
        sql=True,
    )

    captured = capsys.readouterr()
    assert "DROP TABLE conclusion_claims" in captured.out
    assert "DROP TABLE claim_construction_evidence" in captured.out
    assert "DROP TABLE claim_construction_records" in captured.out


def test_alembic_offline_downgrade_planning_revision_compiles(capsys) -> None:
    config = Config("alembic.ini")

    command.downgrade(
        config,
        "0007_research_planning:0006_claim_construction_synthesis",
        sql=True,
    )

    captured = capsys.readouterr()
    assert "DROP TABLE research_plan_proposal_items" in captured.out
    assert "DROP TABLE research_plan_proposals" in captured.out


def test_alembic_offline_downgrade_assisted_extraction_revision_compiles(capsys) -> None:
    config = Config("alembic.ini")

    command.downgrade(
        config,
        "0008_assisted_evidence_extraction:0007_research_planning",
        sql=True,
    )

    captured = capsys.readouterr()
    assert "DROP TABLE evidence_candidate_proposals" in captured.out
    assert "DROP TABLE assisted_evidence_extraction_requests" in captured.out


def test_alembic_offline_downgrade_source_content_revision_compiles(capsys) -> None:
    config = Config("alembic.ini")

    command.downgrade(
        config,
        "0005_source_content_acquisition:0004_external_research_acquisition",
        sql=True,
    )

    captured = capsys.readouterr()
    assert "DROP TABLE evidence_extraction_records" in captured.out
    assert "DROP TABLE source_content_segments" in captured.out
    assert "DROP TABLE source_content_snapshots" in captured.out


def test_migration_file_exists() -> None:
    assert Path("alembic/versions/0001_core_research_data_model.py").is_file()
    assert Path("alembic/versions/0002_claim_validation_foundation.py").is_file()
    assert Path("alembic/versions/0003_research_method_orchestration.py").is_file()
    assert Path("alembic/versions/0004_external_research_acquisition.py").is_file()
    assert Path("alembic/versions/0005_source_content_acquisition.py").is_file()
    assert Path("alembic/versions/0006_claim_construction_synthesis.py").is_file()
    assert Path("alembic/versions/0007_research_planning.py").is_file()
    assert Path("alembic/versions/0008_assisted_evidence_extraction.py").is_file()
