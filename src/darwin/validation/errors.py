"""Claim validation service errors."""


class ClaimValidationError(Exception):
    """Base error for claim validation service failures."""


class ClaimValidationPersistenceError(ClaimValidationError):
    """Raised when validation cannot be persisted safely."""
