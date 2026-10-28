"""Pytest configuration and global test fixtures."""

from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from bankrag.api.main import app
from bankrag.core.config import Settings, get_settings


@pytest.fixture
def test_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[Settings]:
    """Fixture providing clean isolated test settings."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("QDRANT_URL", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("FAKE_LLM", "true")

    # Clear cached get_settings singleton
    get_settings.cache_clear()
    settings = get_settings()
    yield settings
    get_settings.cache_clear()


@pytest.fixture
async def async_client(test_settings: Settings) -> AsyncIterator[AsyncClient]:
    """Async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
