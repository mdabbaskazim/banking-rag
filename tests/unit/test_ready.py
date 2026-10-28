"""Unit tests for /ready endpoint behavior."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from bankrag.api.routes_health import CheckDetail


@pytest.mark.asyncio
async def test_ready_unconfigured_returns_503(async_client: AsyncClient) -> None:
    """When DATABASE_URL and QDRANT_URL are empty, /ready must return 503 not_ready."""
    response = await async_client.get("/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["postgres"]["status"] == "unhealthy"
    assert "DATABASE_URL is not configured" in data["checks"]["postgres"]["detail"]
    assert data["checks"]["qdrant"]["status"] == "unhealthy"
    assert "QDRANT_URL is not configured" in data["checks"]["qdrant"]["detail"]


@pytest.mark.asyncio
async def test_ready_all_healthy_returns_200(async_client: AsyncClient) -> None:
    """When checks pass, /ready must return 200 ready."""
    with (
        patch(
            "bankrag.api.routes_health.check_database_health",
            new_callable=AsyncMock,
            return_value=CheckDetail(status="healthy"),
        ),
        patch(
            "bankrag.api.routes_health.check_qdrant_health",
            new_callable=AsyncMock,
            return_value=CheckDetail(status="healthy"),
        ),
    ):
        response = await async_client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["postgres"]["status"] == "healthy"
        assert data["checks"]["qdrant"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_ready_partial_failure_returns_503(async_client: AsyncClient) -> None:
    """When one service fails, /ready must return 503 and report the exact failure."""
    with (
        patch(
            "bankrag.api.routes_health.check_database_health",
            new_callable=AsyncMock,
            return_value=CheckDetail(status="healthy"),
        ),
        patch(
            "bankrag.api.routes_health.check_qdrant_health",
            new_callable=AsyncMock,
            return_value=CheckDetail(status="unhealthy", detail="Connection timed out"),
        ),
    ):
        response = await async_client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["postgres"]["status"] == "healthy"
        assert data["checks"]["qdrant"]["status"] == "unhealthy"
        assert data["checks"]["qdrant"]["detail"] == "Connection timed out"
