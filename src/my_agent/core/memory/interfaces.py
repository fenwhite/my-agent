from __future__ import annotations

from typing import Protocol

from my_agent.common.message import Message
    
class CompressionStrategy(Protocol):
    def compress(
            self,
            old_summary: str,
            new_message: list[Message],
            token_budget: int,
    ) -> str:
        ...

class ConversationMemory(Protocol):
    @property
    def compressed_summary(self) -> str:
        ...

    @property
    def active_window(self) -> list[Message]:
        ...

    def add_message(self, message: Message) -> None:
        ...

    def get_context_message(self) -> list[Message]:
        ...

    def clear(self) -> None:
        ...

    def load_state(self, compressed_summary: str, active_window: list[Message]) -> None:
        ...

    def get_state(self) -> tuple[str, list[Message]]:
        ...