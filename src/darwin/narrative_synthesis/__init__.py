"""Controlled assisted narrative synthesis exports."""

from darwin.narrative_synthesis.errors import (
    NarrativeSynthesisConfigurationError,
    NarrativeSynthesisContextOverflow,
    NarrativeSynthesisError,
    NarrativeSynthesisProviderError,
    NarrativeSynthesisProviderTimeout,
    NarrativeSynthesisPublicationError,
    NarrativeSynthesisRejectionError,
    NarrativeSynthesisValidationError,
)
from darwin.narrative_synthesis.providers import (
    FakeNarrativeSynthesisProvider,
    NarrativeSynthesisProvider,
    OpenAINarrativeSynthesisProvider,
)
from darwin.narrative_synthesis.schemas import (
    NarrativeFinding,
    NarrativeProposal,
    NarrativeProposalRead,
    NarrativePublicationResult,
    NarrativeRejectionResult,
    NarrativeSynthesisLimits,
    NarrativeSynthesisRequest,
    NarrativeSynthesisResult,
    ProviderNarrativeSynthesisResult,
    SynthesisContext,
)
from darwin.narrative_synthesis.service import NarrativeSynthesisService, render_markdown_report

__all__ = [
    "FakeNarrativeSynthesisProvider",
    "NarrativeFinding",
    "NarrativeProposal",
    "NarrativeProposalRead",
    "NarrativePublicationResult",
    "NarrativeRejectionResult",
    "NarrativeSynthesisConfigurationError",
    "NarrativeSynthesisContextOverflow",
    "NarrativeSynthesisError",
    "NarrativeSynthesisLimits",
    "NarrativeSynthesisProvider",
    "NarrativeSynthesisProviderError",
    "NarrativeSynthesisProviderTimeout",
    "NarrativeSynthesisPublicationError",
    "NarrativeSynthesisRejectionError",
    "NarrativeSynthesisRequest",
    "NarrativeSynthesisResult",
    "NarrativeSynthesisService",
    "NarrativeSynthesisValidationError",
    "OpenAINarrativeSynthesisProvider",
    "ProviderNarrativeSynthesisResult",
    "SynthesisContext",
    "render_markdown_report",
]
