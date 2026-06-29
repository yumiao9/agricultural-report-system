"""Token bucket rate limiter for API calls."""

import asyncio
import time


class TokenBucket:
    """Simple token bucket rate limiter."""

    def __init__(self, rate: float, burst: int = 1):
        """
        Args:
            rate: Number of tokens per second.
            burst: Maximum burst size.
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_refill = time.monotonic()

    async def acquire(self):
        """Wait until a token is available."""
        while True:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= 1:
                self.tokens -= 1
                return

            # Wait until next token would be available
            wait_time = (1 - self.tokens) / self.rate
            await asyncio.sleep(wait_time)


class DomainRateLimiter:
    """Rate limiter keyed by domain name."""

    def __init__(self, default_rate: float = 0.5):
        """
        Args:
            default_rate: Default requests per second per domain.
        """
        self.default_rate = default_rate
        self._buckets: dict[str, TokenBucket] = {}

    def _get_bucket(self, domain: str) -> TokenBucket:
        if domain not in self._buckets:
            self._buckets[domain] = TokenBucket(rate=self.default_rate)
        return self._buckets[domain]

    async def wait(self, domain: str):
        """Wait before making a request to the given domain."""
        bucket = self._get_bucket(domain)
        await bucket.acquire()
