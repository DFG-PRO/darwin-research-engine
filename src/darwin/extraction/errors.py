"""Assisted evidence extraction errors."""


class AssistedExtractionError(Exception):
    """Base error for assisted evidence extraction failures."""


class ExtractionProviderError(AssistedExtractionError):
    """Raised when an extraction provider fails before usable structured output exists."""


class ExtractionProviderTimeout(ExtractionProviderError):
    """Raised when an extraction provider exceeds its bounded timeout."""


class ExtractionConfigurationError(AssistedExtractionError):
    """Raised when a configured extraction provider is not usable."""


class ExtractionValidationError(AssistedExtractionError):
    """Raised when requests or candidates violate structural/provenance rules."""


class EvidenceCandidateAcceptanceError(AssistedExtractionError):
    """Raised when an evidence candidate cannot be accepted."""


class EvidenceCandidateRejectionError(AssistedExtractionError):
    """Raised when an evidence candidate cannot be rejected."""
