from __future__ import annotations

from my_agent.infrastructure.llm.protocols import RetryStrategyProtocol


class NoRetryStrategy(RetryStrategyProtocol):
    async def execute(self, factory):
        return await factory()