"""FastAPI main entrypoint for Banking RAG API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from bankrag.api.routes_health import router as health_router
from bankrag.core.config import get_settings
from bankrag.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: initialize structured logging and handle graceful shutdown."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("application_startup", app_env=settings.app_env, version="0.1.0")

    yield

    logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="Banking RAG API",
        description="Production-grade Banking RAG with verified claims and human-in-the-loop",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health_router)
    return app


app = create_app()
