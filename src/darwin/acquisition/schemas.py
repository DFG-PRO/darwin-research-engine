"""Pydantic contracts for external research acquisition."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from darwin.db.models import (
    AcquisitionStatus,
    SourceCandidateRegistrationStatus,
    SourceType,
    utc_now,
)


class AcquisitionRequest(BaseModel):
    """Structured request to discover source candidates for a research run."""

    model_config = ConfigDict(str_strip_whitespace=True)

    research_run_id: uuid.UUID
    query: str = Field(min_length=1, max_length=500)
    category: str | None = Field(default=None, max_length=128)
    requested_source_types: list[SourceType] = Field(default_factory=list)
    freshness_start: date | None = None
    freshness_end: date | None = None
    domain_constraints: list[str] = Field(default_factory=list, max_length=20)
    result_limit: int = Field(default=10, ge=1, le=50)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_freshness_window(self) -> AcquisitionRequest:
        if (
            self.freshness_start is not None
            and self.freshness_end is not None
            and self.freshness_start > self.freshness_end
        ):
            raise ValueError("freshness_start must be before or equal to freshness_end")
        return self


class ProviderSourceCandidate(BaseModel):
    """Source candidate returned by an acquisition provider."""

    model_config = ConfigDict(str_strip_whitespace=True)

    canonical_locator: str = Field(min_length=1)
    title: str | None = None
    publisher: str | None = None
    publication_date: date | None = None
    retrieved_at: datetime | None = None
    snippet: str | None = None
    provider_rank: int | None = Field(default=None, ge=1)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    source_type: SourceType | None = None
    provider_candidate_id: str | None = None


class ProviderSearchResult(BaseModel):
    """Provider-native result normalized to Darwin's provider boundary."""

    provider_id: str
    provider_request_id: str | None = None
    original_query: str
    executed_at: datetime = Field(default_factory=utc_now)
    status: AcquisitionStatus = AcquisitionStatus.SUCCESS
    candidates: list[ProviderSourceCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    retry_attempts: int = 0
    request_count: int | None = None
    usage_units: Decimal | None = None
    estimated_cost: Decimal | None = None
    actual_cost: Decimal | None = None
    rate_limit_metadata: dict[str, Any] = Field(default_factory=dict)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class SourceCandidateResult(BaseModel):
    """Persisted source candidate result returned to callers."""

    model_config = ConfigDict(from_attributes=True)

    candidate_id: uuid.UUID
    provider_candidate_id: str | None
    canonical_locator: str
    normalized_locator: str
    title: str | None
    publisher: str | None
    normalized_domain: str | None
    publication_date: date | None
    retrieved_at: datetime
    provider_rank: int | None
    source_type: SourceType | None
    registration_status: SourceCandidateRegistrationStatus
    duplicate_of_candidate_id: uuid.UUID | None
    registered_source_id: uuid.UUID | None


class AcquisitionResult(BaseModel):
    """Audited acquisition result exposed to orchestration and CLI boundaries."""

    acquisition_id: uuid.UUID
    research_run_id: uuid.UUID
    provider_id: str
    provider_request_id: str | None
    query: str
    status: AcquisitionStatus
    executed_at: datetime
    completed_at: datetime | None
    candidate_count: int
    registered_source_count: int
    warnings: list[str]
    errors: list[str]
    retry_attempts: int
    request_count: int | None
    candidates: list[SourceCandidateResult]
