"""Errors for controlled assisted narrative synthesis."""


class NarrativeSynthesisError(Exception):
    """Base error for assisted narrative synthesis."""


class NarrativeSynthesisConfigurationError(NarrativeSynthesisError):
    """Provider or runtime configuration is invalid."""


class NarrativeSynthesisProviderError(NarrativeSynthesisError):
    """Narrative synthesis provider failed."""


class NarrativeSynthesisProviderTimeout(NarrativeSynthesisProviderError):
    """Narrative synthesis provider timed out."""


class NarrativeSynthesisValidationError(NarrativeSynthesisError):
    """Narrative proposal or context failed deterministic validation."""


class NarrativeSynthesisContextOverflow(NarrativeSynthesisValidationError):
    """Canonical context cannot fit configured bounded controls."""


class NarrativeSynthesisPublicationError(NarrativeSynthesisError):
    """A proposal cannot be published as a report artifact."""


class NarrativeSynthesisRejectionError(NarrativeSynthesisError):
    """A proposal cannot be rejected."""
