"""Unit tests for fake providers."""

import pytest
from pydantic import BaseModel

from bankrag.core.errors import ProviderError, RateLimitExceededError, VectorStoreError
from bankrag.providers.fakes import (
    FakeLLMProvider,
    FakeRateLimiterProvider,
    FakeVectorStoreProvider,
)


class SampleClaim(BaseModel):
    statement: str
    confidence: float


@pytest.mark.asyncio
async def test_fake_llm_text() -> None:
    fake = FakeLLMProvider(canned_text="The interest rate is 4.5%")
    text = await fake.generate("What is the interest rate?")
    assert text == "The interest rate is 4.5%"
    assert len(fake.call_history) == 1


@pytest.mark.asyncio
async def test_fake_llm_structured() -> None:
    expected = SampleClaim(statement="Fixed deposits are insured up to 5 lakhs", confidence=0.99)
    fake = FakeLLMProvider(canned_structured=expected)

    result = await fake.generate_structured("Tell me about deposit insurance", SampleClaim)
    assert result.statement == expected.statement
    assert result.confidence == expected.confidence


@pytest.mark.asyncio
async def test_fake_llm_failure() -> None:
    fake = FakeLLMProvider(should_fail=True)
    with pytest.raises(ProviderError):
        await fake.generate("Test prompt")


@pytest.mark.asyncio
async def test_fake_vector_store() -> None:
    store = FakeVectorStoreProvider(is_healthy=True)
    assert await store.is_healthy() is True

    test_points = [{"id": "chunk_1", "vector": [0.1, 0.2], "payload": {"text": "sample"}}]
    await store.upsert(test_points)

    results = await store.search([0.1, 0.2], limit=5)
    assert len(results) == 1
    assert results[0]["id"] == "chunk_1"

    store.set_healthy(False)
    assert await store.is_healthy() is False
    with pytest.raises(VectorStoreError):
        await store.search([0.1, 0.2])


@pytest.mark.asyncio
async def test_fake_rate_limiter() -> None:
    limiter = FakeRateLimiterProvider()
    await limiter.acquire(estimated_tokens=50)
    assert limiter.acquired_count == 1

    limiter.record_usage(actual_tokens=42)
    assert limiter.total_tokens_recorded == 42

    blocking_limiter = FakeRateLimiterProvider(should_block=True)
    with pytest.raises(RateLimitExceededError):
        await blocking_limiter.acquire(10)
