from __future__ import annotations

from typing import Protocol, TypeVar, Awaitable, Callable

from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

T = TypeVar("T")

class RetryStrategyProtocol(Protocol):
    async def execute(
            self,
            factory: Callable[[], Awaitable[T]],
    ) -> T:
        ...


class RateLimiterProtocol(Protocol):
    async def acquire(self) -> None:
        ...