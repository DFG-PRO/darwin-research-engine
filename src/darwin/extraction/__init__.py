"""Controlled assisted evidence extraction boundary."""

from darwin.extraction.errors import (
    AssistedExtractionError,
    EvidenceCandidateAcceptanceError,
    EvidenceCandidateRejectionError,
    ExtractionConfigurationError,
    ExtractionProviderError,
    ExtractionProviderTimeout,
    ExtractionValidationError,
)
from darwin.extraction.providers import (
    EvidenceExtractionProvider,
    FakeEvidenceExtractionProvider,
    OpenAIEvidenceExtractionProvider,
)
from darwin.extraction.schemas import (
    AssistedEvidenceExtractionRequest,
    AssistedExtractionLimits,
    AssistedExtractionResult,
    EvidenceCandidateAcceptanceResult,
    EvidenceCandidateProposal,
    EvidenceCandidateRead,
    EvidenceCandidateRejectionResult,
    ProviderEvidenceExtractionResult,
    SegmentForExtraction,
)
from darwin.extraction.service import AssistedEvidenceExtractionService

__all__ = [
    "AssistedEvidenceExtractionRequest",
    "AssistedEvidenceExtractionService",
    "AssistedExtractionError",
    "AssistedExtractionLimits",
    "AssistedExtractionResult",
    "EvidenceCandidateAcceptanceError",
    "EvidenceCandidateAcceptanceResult",
    "EvidenceCandidateProposal",
    "EvidenceCandidateRead",
    "EvidenceCandidateRejectionError",
    "EvidenceCandidateRejectionResult",
    "EvidenceExtractionProvider",
    "ExtractionConfigurationError",
    "ExtractionProviderError",
    "ExtractionProviderTimeout",
    "ExtractionValidationError",
    "FakeEvidenceExtractionProvider",
    "OpenAIEvidenceExtractionProvider",
    "ProviderEvidenceExtractionResult",
    "SegmentForExtraction",
]
