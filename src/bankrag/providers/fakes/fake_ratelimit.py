"""Fake rate limiter provider for unit testing."""

from bankrag.core.errors import RateLimitExceededError
from bankrag.providers.interfaces import RateLimiterProvider


class FakeRateLimiterProvider(RateLimiterProvider):
    """In-memory fake rate limiter for unit tests."""

    def __init__(self, should_block: bool = False) -> None:
        self.should_block = should_block
        self.acquired_count = 0
        self.total_tokens_recorded = 0

    async def acquire(self, estimated_tokens: int = 1) -> None:
        if self.should_block:
            raise RateLimitExceededError("Rate limit exceeded (simulated)")
        self.acquired_count += 1

    def record_usage(self, actual_tokens: int) -> None:
        self.total_tokens_recorded += actual_tokens
