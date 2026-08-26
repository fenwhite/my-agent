from __future__ import annotations

from aiolimiter import AsyncLimiter

from rag_agent.infrastructure.llm.protocols import RateLimiterProtocol
from rag_agent.config.settings import get_settings

class AsyncRateLimiter(RateLimiterProtocol):
    def __init__(self, qps: int) -> None:
        if qps is None:
            qps = get_settings().qps_limit
        self._limiter = AsyncLimiter(max_rate=qps, time_period=1)

    async def acquire(self) -> None:
        await self._limiter.acquire()