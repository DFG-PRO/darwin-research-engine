"""Errors for controlled research loop execution."""


class ResearchLoopError(Exception):
    """Base error for research loop execution."""


class ResearchLoopValidationError(ResearchLoopError):
    """Research loop request or transition is invalid."""


class ResearchLoopBudgetError(ResearchLoopError):
    """A hard loop budget would be exceeded."""


class ResearchLoopIntegrityError(ResearchLoopError):
    """Loop detected an integrity boundary violation."""


class ResearchLoopResumeError(ResearchLoopError):
    """Loop execution cannot be resumed from its current state."""
