"""Unit tests for exception hierarchy."""

from bankrag.core.errors import (
    BankRagError,
    CircuitBreakerOpenError,
    ConfigurationError,
    DatabaseError,
    ProviderError,
    RateLimitExceededError,
    ServiceUnavailableError,
    VectorStoreError,
    VerificationError,
)


def test_exception_inheritance() -> None:
    assert issubclass(ConfigurationError, BankRagError)
    assert issubclass(ProviderError, BankRagError)
    assert issubclass(RateLimitExceededError, ProviderError)
    assert issubclass(CircuitBreakerOpenError, ProviderError)
    assert issubclass(DatabaseError, BankRagError)
    assert issubclass(VectorStoreError, BankRagError)
    assert issubclass(VerificationError, BankRagError)
    assert issubclass(ServiceUnavailableError, BankRagError)


def test_exception_message() -> None:
    err = ConfigurationError("Missing key")
    assert err.message == "Missing key"
    assert str(err) == "Missing key"
