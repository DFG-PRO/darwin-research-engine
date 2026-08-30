"""Assisted claim construction errors."""


class AssistedClaimConstructionError(Exception):
    """Base error for assisted claim construction failures."""


class ClaimConstructionProviderError(AssistedClaimConstructionError):
    """Raised when a provider fails before usable structured output exists."""


class ClaimConstructionProviderTimeout(ClaimConstructionProviderError):
    """Raised when a provider exceeds its bounded timeout."""


class ClaimConstructionConfigurationError(AssistedClaimConstructionError):
    """Raised when a configured claim construction provider is unusable."""


class ClaimCandidateValidationError(AssistedClaimConstructionError):
    """Raised when a claim candidate violates structure or provenance."""


class ClaimCandidateAcceptanceError(AssistedClaimConstructionError):
    """Raised when a claim candidate cannot be accepted."""


class ClaimCandidateRejectionError(AssistedClaimConstructionError):
    """Raised when a claim candidate cannot be rejected."""
