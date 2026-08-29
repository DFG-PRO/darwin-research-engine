"""Research service errors."""


class ResearchServiceError(Exception):
    """Base error for research persistence service failures."""


class ResearchRunNotFound(ResearchServiceError):
    """Raised when a research run cannot be found."""


class InvalidResearchRunTransition(ResearchServiceError):
    """Raised when a research run lifecycle transition is not allowed."""


class InvalidResearchRelationship(ResearchServiceError):
    """Raised when related research records violate structural rules."""


class DuplicateResearchRelationship(ResearchServiceError):
    """Raised when a duplicate claim/evidence relationship is requested."""
