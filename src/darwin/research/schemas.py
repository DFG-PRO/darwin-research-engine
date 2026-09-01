"""Read models for persisted research records."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from darwin.db.models import (
    ClaimEvidenceRelation,
    ClaimStatus,
    ClaimType,
    ConclusionStatus,
    EvidenceType,
    ResearchRunStatus,
    SourceType,
)


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    source_type: SourceType
    canonical_locator: str
    title: str | None
    publisher: str | None
    publication_date: date | None
    retrieved_at: datetime
    content_fingerprint: str | None
    metadata: dict[str, Any] = Field(alias="source_metadata")
    created_at: datetime


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    research_run_id: uuid.UUID
    source_id: uuid.UUID
    evidence_type: EvidenceType
    statement: str
    source_locator: str | None
    captured_at: datetime
    metadata: dict[str, Any] = Field(alias="evidence_metadata")


class ClaimEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim_id: uuid.UUID
    evidence_id: uuid.UUID
    relation: ClaimEvidenceRelation
    created_at: datetime


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    research_run_id: uuid.UUID
    statement: str
    claim_type: ClaimType
    status: ClaimStatus
    confidence: Decimal | None
    created_at: datetime
    updated_at: datetime


class ConclusionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    research_run_id: uuid.UUID
    statement: str
    confidence: Decimal | None
    status: ConclusionStatus
    created_at: datetime
    updated_at: datetime


class ResearchRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_id: str
    title: str
    status: ResearchRunStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    research_method_version: str
    darwin_version: str
    context: dict[str, Any]


class ResearchRunSummaryRead(BaseModel):
    """Compact read model for listing persisted research runs."""

    id: uuid.UUID
    public_id: str
    title: str
    status: ResearchRunStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    research_method_version: str
    darwin_version: str
    source_count: int
    evidence_count: int
    claim_count: int
    conclusion_count: int


class ResearchRecordRead(BaseModel):
    """Traceable read model for one persisted research run."""

    research_run: ResearchRunRead
    sources: list[SourceRead]
    evidence: list[EvidenceRead]
    claims: list[ClaimRead]
    claim_evidence: list[ClaimEvidenceRead]
    conclusions: list[ConclusionRead]


class ResearchRecordExportSummaryRead(BaseModel):
    """Aggregate counts included in a research record export."""

    source_count: int
    evidence_count: int
    claim_count: int
    claim_evidence_count: int
    conclusion_count: int


class ResearchRecordExportRead(ResearchRecordRead):
    """JSON export envelope for one traceable research record."""

    schema_version: str = "research-record-export.v1"
    exported_at: datetime
    summary: ResearchRecordExportSummaryRead
