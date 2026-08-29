"""Read models for claim validation results."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from darwin.db.models import ClaimValidationReasonCode, ClaimValidationState


class ClaimValidationResult(BaseModel):
    """Structured deterministic validation result for a claim."""

    model_config = ConfigDict(from_attributes=True)

    claim_id: uuid.UUID
    validation_state: ClaimValidationState
    supporting_evidence_count: int
    contradicting_evidence_count: int
    contextual_evidence_count: int
    distinct_source_count: int
    independent_supporting_source_count: int
    independent_contradicting_source_count: int
    independent_corroboration_exists: bool
    contradiction_exists: bool
    human_review_requested: bool
    human_validation_present: bool
    reason_codes: list[ClaimValidationReasonCode]
    evaluated_at: datetime
    validation_method_version: str
