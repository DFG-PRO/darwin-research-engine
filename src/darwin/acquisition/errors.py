"""Errors for external research acquisition."""

from __future__ import annotations


class AcquisitionError(Exception):
    """Base error for acquisition-layer failures."""


class AcquisitionProviderError(AcquisitionError):
    """External provider failed without returning a usable result."""


class AcquisitionProviderTimeout(AcquisitionProviderError):
    """External provider timed out."""


class AcquisitionConfigurationError(AcquisitionError):
    """Provider configuration is missing or invalid."""
