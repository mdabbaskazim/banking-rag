"""Health and Readiness endpoints.

Complies with ARCHITECTURE.md Section 9 & 12:
- /health does no I/O, does not touch the database or network.
- /ready checks Neon Postgres and Qdrant only when called on demand.
"""

import asyncio

import psycopg
from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from bankrag.core.config import Settings, get_settings
from bankrag.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["monitoring"])


class HealthResponse(BaseModel):
    status: str
    app_env: str
    version: str = "0.1.0"


class CheckDetail(BaseModel):
    status: str  # "healthy" or "unhealthy"
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: str  # "ready" or "not_ready"
    checks: dict[str, CheckDetail]


def _sync_check_postgres(conn_str: str) -> None:
    """Synchronous connection check executed in a thread pool to avoid Windows event loop issues."""
    with psycopg.connect(conn_str, connect_timeout=3) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")


async def check_database_health(settings: Settings) -> CheckDetail:
    """Check connectivity to Postgres database without keeping a persistent connection."""
    if not settings.database_url:
        return CheckDetail(status="unhealthy", detail="DATABASE_URL is not configured")

    conn_str = settings.database_url
    if conn_str.startswith("postgresql+psycopg://"):
        conn_str = conn_str.replace("postgresql+psycopg://", "postgresql://", 1)

    try:
        await asyncio.to_thread(_sync_check_postgres, conn_str)
        return CheckDetail(status="healthy")
    except Exception as exc:
        logger.warning("readiness_check_db_failed", error=str(exc))
        return CheckDetail(status="unhealthy", detail=str(exc))


async def check_qdrant_health(settings: Settings) -> CheckDetail:
    """Check connectivity to Qdrant cluster."""
    if not settings.qdrant_url:
        return CheckDetail(status="unhealthy", detail="QDRANT_URL is not configured")

    try:
        from qdrant_client import AsyncQdrantClient

        client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=3,
        )
        # Attempt lightweight collections fetch
        await client.get_collections()
        await client.close()
        return CheckDetail(status="healthy")
    except Exception as exc:
        logger.warning("readiness_check_qdrant_failed", error=str(exc))
        return CheckDetail(status="unhealthy", detail=str(exc))


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    """Liveness probe. Independent of network calls and database access."""
    settings = get_settings()
    return HealthResponse(status="ok", app_env=settings.app_env)


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    responses={
        200: {"description": "All required dependencies are reachable"},
        503: {"description": "One or more dependencies are not reachable"},
    },
)
async def ready(response: Response) -> ReadinessResponse:
    """Readiness probe. Verifies Neon Postgres and Qdrant connectivity."""
    settings = get_settings()

    db_check = await check_database_health(settings)
    qdrant_check = await check_qdrant_health(settings)

    all_healthy = db_check.status == "healthy" and qdrant_check.status == "healthy"

    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if all_healthy else "not_ready",
        checks={
            "postgres": db_check,
            "qdrant": qdrant_check,
        },
    )
