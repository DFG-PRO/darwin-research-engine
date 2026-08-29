"""Centralized application settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings for local development and deployment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DARWIN_",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    env: Literal["local", "test", "staging", "production"] = "local"
    log_level: str = "INFO"
    darwin_version: str = Field(
        default="0.1.0",
        validation_alias=AliasChoices("DARWIN_VERSION", "DARWIN_DARWIN_VERSION"),
        description="Darwin application version for the v0.1 foundation.",
    )
    research_method_version: str = Field(
        default="0.1.0",
        description="Version identifier for the research method contract.",
    )
    artifact_root: Path = Field(
        default=Path("artifacts"),
        description="Root directory for local runtime artifacts.",
    )
    database_url: str = Field(
        default="postgresql+psycopg://darwin:darwin@localhost:5432/darwin",
        description="SQLAlchemy database URL for Darwin's PostgreSQL database.",
    )
    external_search_provider: Literal["fake", "brave"] = Field(
        default="fake",
        description="External source discovery provider identifier.",
    )
    external_search_timeout_seconds: float = Field(
        default=10.0,
        ge=0.1,
        description="HTTP timeout for external source discovery requests.",
    )
    external_search_max_retries: int = Field(
        default=1,
        ge=0,
        le=3,
        description="Maximum bounded retry count for external source discovery.",
    )
    external_search_user_agent: str = Field(
        default="DarwinResearchEngine/0.1",
        description="User-Agent sent by HTTP-based external discovery providers.",
    )
    brave_search_api_key: SecretStr | None = Field(
        default=None,
        description="Brave Search API credential. Never commit real values.",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached process settings."""

    return Settings()
