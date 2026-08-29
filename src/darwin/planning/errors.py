"""Research planning errors."""


class ResearchPlanningError(Exception):
    """Base error for controlled research planning failures."""


class PlanningProviderError(ResearchPlanningError):
    """Raised when a planning provider fails before valid structured output exists."""


class PlanningProviderTimeout(PlanningProviderError):
    """Raised when a planning provider exceeds its bounded timeout."""


class PlanningConfigurationError(ResearchPlanningError):
    """Raised when a configured planning provider is not usable."""


class PlanningValidationError(ResearchPlanningError):
    """Raised when a generated planning proposal violates structural rules."""


class PlanningApprovalError(ResearchPlanningError):
    """Raised when a proposal cannot be approved into a research run."""
