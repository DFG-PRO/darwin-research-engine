"""External research acquisition foundation."""

from darwin.acquisition.errors import (
    AcquisitionConfigurationError,
    AcquisitionError,
    AcquisitionProviderError,
    AcquisitionProviderTimeout,
)
from darwin.acquisition.providers import BraveSearchProvider, FakeResearchProvider, ResearchProvider
from darwin.acquisition.schemas import (
    AcquisitionRequest,
    AcquisitionResult,
    ProviderSearchResult,
    ProviderSourceCandidate,
    SourceCandidateResult,
)
from darwin.acquisition.service import AcquisitionService

__all__ = [
    "AcquisitionConfigurationError",
    "AcquisitionError",
    "AcquisitionProviderError",
    "AcquisitionProviderTimeout",
    "AcquisitionRequest",
    "AcquisitionResult",
    "AcquisitionService",
    "BraveSearchProvider",
    "FakeResearchProvider",
    "ProviderSearchResult",
    "ProviderSourceCandidate",
    "ResearchProvider",
    "SourceCandidateResult",
]
