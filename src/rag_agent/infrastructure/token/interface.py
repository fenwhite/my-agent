from __future__ import annotations

from typing import Any, Protocol

from rag_agent.common.message import Message

class TokenCounter(Protocol):
    def count_tokens(self, text: str) -> int:
        ...

    def count_messages_tokens(self, messages: list[Message]) -> int:
        ...