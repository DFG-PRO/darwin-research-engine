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
    source_fetch_timeout_seconds: float = Field(
        default=10.0,
        ge=0.1,
        description="HTTP timeout for source content fetch requests.",
    )
    source_fetch_max_retries: int = Field(
        default=1,
        ge=0,
        le=3,
        description="Maximum bounded retry count for source content fetches.",
    )
    source_fetch_user_agent: str = Field(
        default="DarwinResearchEngine/0.1",
        description="User-Agent sent by HTTP source content fetches.",
    )
    source_fetch_max_bytes: int = Field(
        default=1_000_000,
        ge=1024,
        description="Maximum raw response bytes persisted for one source content fetch.",
    )
    source_content_retrieval_method_version: str = Field(
        default="source-fetch-http-1.8g",
        description="Version identifier for source content retrieval.",
    )
    source_content_normalization_method_version: str = Field(
        default="html-text-normalization-1.8g",
        description="Version identifier for deterministic source content normalization.",
    )
    evidence_extraction_method_version: str = Field(
        default="segment-extraction-1.8g",
        description="Version identifier for explicit segment/span evidence extraction.",
    )
    evidence_excerpt_max_chars: int = Field(
        default=4000,
        ge=1,
        description="Maximum characters allowed in one extracted Evidence excerpt.",
    )
    claim_construction_method_version: str = Field(
        default="manual-explicit-claim-construction-1.8h",
        description="Version identifier for explicit evidence-to-claim construction.",
    )
    structured_synthesis_method_version: str = Field(
        default="structured-synthesis-1.8h",
        description="Version identifier for deterministic evidence-grounded synthesis.",
    )
    claim_statement_max_chars: int = Field(
        default=2000,
        ge=1,
        description="Maximum characters allowed in one constructed Claim statement.",
    )
    research_planning_provider: Literal["fake", "openai"] = Field(
        default="fake",
        description="Planning provider identifier. Fake is deterministic and network-free.",
    )
    research_planning_model: str = Field(
        default="fake-deterministic-planner-v1",
        description="Provider model identifier for research planning proposals.",
    )
    research_planning_method_version: str = Field(
        default="research-planning-1.9a",
        description="Version identifier for the planner method contract.",
    )
    research_planning_prompt_version: str = Field(
        default="research-planning-prompt-1.9a",
        description="Version identifier for LLM planning prompt semantics.",
    )
    research_planning_schema_version: str = Field(
        default="research-plan-proposal-schema-1.9a",
        description="Version identifier for structured planning output.",
    )
    research_planning_timeout_seconds: float = Field(
        default=20.0,
        ge=0.1,
        description="HTTP timeout for configured live planning providers.",
    )
    research_planning_max_plan_items: int = Field(
        default=8,
        ge=1,
        le=25,
        description="Maximum proposed plan items accepted by the planner.",
    )
    research_planning_max_required_plan_items: int = Field(
        default=6,
        ge=1,
        le=25,
        description="Maximum required plan items accepted by the planner.",
    )
    research_planning_max_categories: int = Field(
        default=6,
        ge=1,
        le=20,
        description="Maximum research categories accepted by the planner.",
    )
    research_planning_max_breadth: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum source breadth hint accepted in planning requests.",
    )
    research_planning_max_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum search depth hint accepted in planning requests.",
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        description="OpenAI API credential for optional live providers. Never persisted.",
    )
    assisted_evidence_extraction_provider: Literal["fake", "openai"] = Field(
        default="fake",
        description="Assisted evidence extraction provider identifier.",
    )
    assisted_evidence_extraction_model: str = Field(
        default="fake-evidence-extractor-v1",
        description="Provider model identifier for assisted evidence extraction.",
    )
    assisted_evidence_extraction_method_version: str = Field(
        default="assisted-evidence-extraction-1.9b",
        description="Version identifier for assisted evidence extraction.",
    )
    assisted_evidence_extraction_prompt_version: str = Field(
        default="assisted-evidence-extraction-prompt-1.9b",
        description="Version identifier for assisted extraction prompt semantics.",
    )
    assisted_evidence_extraction_schema_version: str = Field(
        default="evidence-candidate-proposal-schema-1.9b",
        description="Version identifier for assisted extraction structured output.",
    )
    assisted_evidence_extraction_timeout_seconds: float = Field(
        default=20.0,
        ge=0.1,
        description="HTTP timeout for configured live extraction providers.",
    )
    assisted_evidence_extraction_max_segments: int = Field(
        default=5,
        ge=1,
        le=25,
        description="Maximum source content segments per assisted extraction request.",
    )
    assisted_evidence_extraction_max_candidates: int = Field(
        default=5,
        ge=1,
        le=25,
        description="Maximum evidence candidates per assisted extraction request.",
    )
    assisted_evidence_extraction_max_segment_chars: int = Field(
        default=4000,
        ge=1,
        description="Maximum characters allowed in any submitted segment.",
    )
    assisted_evidence_extraction_max_total_request_chars: int = Field(
        default=12000,
        ge=1,
        description="Maximum total segment characters submitted in one extraction request.",
    )
    assisted_claim_construction_provider: Literal["fake", "openai"] = Field(
        default="fake",
        description="Assisted claim construction provider identifier.",
    )
    assisted_claim_construction_model: str = Field(
        default="fake-claim-constructor-v1",
        description="Provider model identifier for assisted claim construction.",
    )
    assisted_claim_construction_method_version: str = Field(
        default="assisted-claim-construction-1.9c",
        description="Version identifier for assisted claim construction.",
    )
    assisted_claim_construction_prompt_version: str = Field(
        default="assisted-claim-construction-prompt-1.9c",
        description="Version identifier for assisted claim construction prompt semantics.",
    )
    assisted_claim_construction_schema_version: str = Field(
        default="claim-candidate-proposal-schema-1.9c",
        description="Version identifier for assisted claim construction structured output.",
    )
    assisted_claim_construction_timeout_seconds: float = Field(
        default=20.0,
        ge=0.1,
        description="HTTP timeout for configured live claim construction providers.",
    )
    assisted_claim_construction_max_evidence_items: int = Field(
        default=8,
        ge=1,
        le=50,
        description="Maximum Evidence items per assisted claim construction request.",
    )
    assisted_claim_construction_max_evidence_chars: int = Field(
        default=12000,
        ge=1,
        description="Maximum total Evidence characters in one claim construction request.",
    )
    assisted_claim_construction_max_candidates: int = Field(
        default=5,
        ge=1,
        le=25,
        description="Maximum Claim candidates per assisted claim construction request.",
    )
    assisted_claim_construction_max_claim_chars: int = Field(
        default=1000,
        ge=1,
        description="Maximum characters allowed in one assisted Claim candidate.",
    )
    assisted_claim_construction_max_qualifiers: int = Field(
        default=6,
        ge=0,
        le=25,
        description="Maximum qualifier entries per assisted Claim candidate.",
    )
    assisted_claim_construction_max_assumptions: int = Field(
        default=6,
        ge=0,
        le=25,
        description="Maximum assumption entries per assisted Claim candidate.",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached process settings."""

    return Settings()
