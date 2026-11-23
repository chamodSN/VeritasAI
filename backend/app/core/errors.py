class VeritasError(Exception):
    """Base exception for all application-specific errors."""


class ExternalServiceError(VeritasError):
    """Raised when an external service fails."""


class LLMError(VeritasError):
    """Raised when a language model operation fails."""


class ValidationFailed(VeritasError):
    """Raised when application input validation fails."""
