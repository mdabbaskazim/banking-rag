"""Fake VectorStore provider for zero-credential unit testing."""

from typing import Any

from bankrag.core.errors import VectorStoreError
from bankrag.providers.interfaces import VectorStoreProvider


class FakeVectorStoreProvider(VectorStoreProvider):
    """In-memory fake vector store simulating Qdrant."""

    def __init__(self, is_healthy: bool = True) -> None:
        self._healthy = is_healthy
        self.points: list[dict[str, Any]] = []

    def set_healthy(self, healthy: bool) -> None:
        self._healthy = healthy

    async def search(
        self,
        query_dense: list[float],
        limit: int = 10,
        filter_criteria: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if not self._healthy:
            raise VectorStoreError("Fake vector store is unhealthy")
        # Return points up to limit
        return self.points[:limit]

    async def upsert(self, points: list[dict[str, Any]]) -> None:
        if not self._healthy:
            raise VectorStoreError("Fake vector store is unhealthy")
        self.points.extend(points)

    async def is_healthy(self) -> bool:
        return self._healthy
