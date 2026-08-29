from darwin.config import Settings


def test_settings_defaults_are_safe_for_local_development() -> None:
    settings = Settings(_env_file=None)

    assert settings.env == "local"
    assert settings.log_level == "INFO"
    assert settings.darwin_version == "0.1.0"
    assert settings.research_method_version == "0.1.0"
    assert str(settings.artifact_root) == "artifacts"
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.external_search_provider == "fake"
    assert settings.external_search_timeout_seconds == 10.0
    assert settings.external_search_max_retries == 1
    assert settings.brave_search_api_key is None
    assert settings.source_fetch_timeout_seconds == 10.0
    assert settings.source_fetch_max_retries == 1
    assert settings.source_fetch_max_bytes == 1_000_000
    assert settings.source_content_retrieval_method_version == "source-fetch-http-1.8g"
    assert settings.source_content_normalization_method_version == "html-text-normalization-1.8g"
    assert settings.evidence_extraction_method_version == "segment-extraction-1.8g"
    assert settings.evidence_excerpt_max_chars == 4000
    assert settings.claim_construction_method_version == "manual-explicit-claim-construction-1.8h"
    assert settings.structured_synthesis_method_version == "structured-synthesis-1.8h"
    assert settings.claim_statement_max_chars == 2000


def test_settings_can_be_initialized_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DARWIN_ENV", "test")
    monkeypatch.setenv("DARWIN_VERSION", "0.1.1")
    monkeypatch.setenv("DARWIN_RESEARCH_METHOD_VERSION", "method-2026-08")
    monkeypatch.setenv("DARWIN_ARTIFACT_ROOT", "/tmp/darwin-artifacts")
    monkeypatch.setenv("DARWIN_DATABASE_URL", "postgresql+psycopg://user:pass@db:5432/test")
    monkeypatch.setenv("DARWIN_EXTERNAL_SEARCH_PROVIDER", "brave")
    monkeypatch.setenv("DARWIN_EXTERNAL_SEARCH_TIMEOUT_SECONDS", "3.5")
    monkeypatch.setenv("DARWIN_EXTERNAL_SEARCH_MAX_RETRIES", "2")
    monkeypatch.setenv("DARWIN_BRAVE_SEARCH_API_KEY", "test-secret")
    monkeypatch.setenv("DARWIN_SOURCE_FETCH_TIMEOUT_SECONDS", "4.5")
    monkeypatch.setenv("DARWIN_SOURCE_FETCH_MAX_RETRIES", "2")
    monkeypatch.setenv("DARWIN_SOURCE_FETCH_MAX_BYTES", "2048")
    monkeypatch.setenv("DARWIN_EVIDENCE_EXCERPT_MAX_CHARS", "500")
    monkeypatch.setenv("DARWIN_CLAIM_CONSTRUCTION_METHOD_VERSION", "construct-test")
    monkeypatch.setenv("DARWIN_STRUCTURED_SYNTHESIS_METHOD_VERSION", "synthesis-test")
    monkeypatch.setenv("DARWIN_CLAIM_STATEMENT_MAX_CHARS", "300")

    settings = Settings(_env_file=None)

    assert settings.env == "test"
    assert settings.darwin_version == "0.1.1"
    assert settings.research_method_version == "method-2026-08"
    assert str(settings.artifact_root) == "/tmp/darwin-artifacts"
    assert settings.database_url == "postgresql+psycopg://user:pass@db:5432/test"
    assert settings.external_search_provider == "brave"
    assert settings.external_search_timeout_seconds == 3.5
    assert settings.external_search_max_retries == 2
    assert settings.brave_search_api_key is not None
    assert settings.brave_search_api_key.get_secret_value() == "test-secret"
    assert settings.source_fetch_timeout_seconds == 4.5
    assert settings.source_fetch_max_retries == 2
    assert settings.source_fetch_max_bytes == 2048
    assert settings.evidence_excerpt_max_chars == 500
    assert settings.claim_construction_method_version == "construct-test"
    assert settings.structured_synthesis_method_version == "synthesis-test"
    assert settings.claim_statement_max_chars == 300
