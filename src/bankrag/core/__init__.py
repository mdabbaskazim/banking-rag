"""Core modules for Banking RAG: configuration, logging, errors, and IDs."""

from bankrag.core.config import Settings, get_settings
from bankrag.core.errors import (
    BankRagError,
    CircuitBreakerOpenError,
    ConfigurationError,
    DatabaseError,
    ProviderError,
    RateLimitExceededError,
    VectorStoreError,
    VerificationError,
)
from bankrag.core.ids import generate_chunk_id, generate_thread_id
from bankrag.core.logging import configure_logging, get_logger

__all__ = [
    "BankRagError",
    "CircuitBreakerOpenError",
    "ConfigurationError",
    "DatabaseError",
    "ProviderError",
    "RateLimitExceededError",
    "Settings",
    "VectorStoreError",
    "VerificationError",
    "configure_logging",
    "generate_chunk_id",
    "generate_thread_id",
    "get_logger",
    "get_settings",
]
