from darwin.config import Settings


def test_settings_defaults_are_safe_for_local_development() -> None:
    settings = Settings(_env_file=None)

    assert settings.env == "local"
    assert settings.log_level == "INFO"
    assert settings.darwin_version == "0.1.0"
    assert settings.research_method_version == "0.1.0"
    assert str(settings.artifact_root) == "artifacts"
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_settings_can_be_initialized_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DARWIN_ENV", "test")
    monkeypatch.setenv("DARWIN_VERSION", "0.1.1")
    monkeypatch.setenv("DARWIN_RESEARCH_METHOD_VERSION", "method-2026-08")
    monkeypatch.setenv("DARWIN_ARTIFACT_ROOT", "/tmp/darwin-artifacts")
    monkeypatch.setenv("DARWIN_DATABASE_URL", "postgresql+psycopg://user:pass@db:5432/test")

    settings = Settings(_env_file=None)

    assert settings.env == "test"
    assert settings.darwin_version == "0.1.1"
    assert settings.research_method_version == "method-2026-08"
    assert str(settings.artifact_root) == "/tmp/darwin-artifacts"
    assert settings.database_url == "postgresql+psycopg://user:pass@db:5432/test"
