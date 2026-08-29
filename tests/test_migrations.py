from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_script_directory_loads_revision() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    assert script.get_current_head() == "0002_claim_validation_foundation"


def test_alembic_offline_upgrade_compiles(capsys) -> None:
    config = Config("alembic.ini")

    command.upgrade(config, "head", sql=True)

    captured = capsys.readouterr()
    assert "CREATE TABLE research_runs" in captured.out
    assert "CREATE TABLE evidence" in captured.out
    assert "CREATE TABLE claim_evidence" in captured.out
    assert "CREATE TABLE claim_validation_evaluations" in captured.out
    assert "CREATE TABLE claim_human_validations" in captured.out
    assert "COMMIT;" in captured.out


def test_migration_file_exists() -> None:
    assert Path("alembic/versions/0001_core_research_data_model.py").is_file()
    assert Path("alembic/versions/0002_claim_validation_foundation.py").is_file()
