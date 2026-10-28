"""Core exception classes for Banking RAG."""


class BankRagError(Exception):
    """Base exception for all Banking RAG errors."""

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class ConfigurationError(BankRagError):
    """Raised when configuration is invalid or missing required variables."""


class ProviderError(BankRagError):
    """Base exception for external provider errors (LLM, Vector Store, Embeddings)."""


class RateLimitExceededError(ProviderError):
    """Raised when request or token rate limits are exceeded."""


class CircuitBreakerOpenError(ProviderError):
    """Raised when a call is attempted against an open circuit breaker."""


class DatabaseError(BankRagError):
    """Raised when relational database operations fail."""


class VectorStoreError(BankRagError):
    """Raised when vector database operations fail."""


class VerificationError(BankRagError):
    """Raised when deterministic or entailment claim verification fails."""


class ServiceUnavailableError(BankRagError):
    """Raised when required upstream services are unavailable."""
