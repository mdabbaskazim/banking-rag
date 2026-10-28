"""Provider abstract base classes (interfaces) for Banking RAG.

Complies with ARCHITECTURE.md Section 1 Rule 4:
Every provider sits behind an interface with a fake implementation.
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Abstract interface for LLM client providers."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate unstructured text response from the model."""

    @abstractmethod
    async def generate_structured(self, prompt: str, response_model: type[T], **kwargs: Any) -> T:
        """Generate structured response conforming to the given Pydantic model."""


class VectorStoreProvider(ABC):
    """Abstract interface for vector database providers."""

    @abstractmethod
    async def search(
        self,
        query_dense: list[float],
        limit: int = 10,
        filter_criteria: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search vector collection returning matching points and payloads."""

    @abstractmethod
    async def upsert(self, points: list[dict[str, Any]]) -> None:
        """Upsert points into the collection."""

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Return True if vector store is reachable and operational."""


class RateLimiterProvider(ABC):
    """Abstract interface for client-side rate limiting."""

    @abstractmethod
    async def acquire(self, estimated_tokens: int = 1) -> None:
        """Wait until a request and the estimated tokens are within quota."""

    @abstractmethod
    def record_usage(self, actual_tokens: int) -> None:
        """Reconcile estimated tokens with actual usage from provider response."""


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding providers."""

    @abstractmethod
    async def embed_dense(self, texts: list[str]) -> list[list[float]]:
        """Compute dense vector embeddings for input strings."""


class EntailmentProvider(ABC):
    """Abstract interface for claim verification entailment providers."""

    @abstractmethod
    async def score_entailment(self, premise: str, hypothesis: str) -> float:
        """Return confidence score in [0.0, 1.0] that premise entails hypothesis."""
