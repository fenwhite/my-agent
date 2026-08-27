"""对话记忆管理模块。

提供基于 Token 预算的滑动窗口、增量压缩、Tool Call 保护和跨会话恢复能力。
"""

from my_agent.infrastructure.memory.interfaces import (
    Message,
    TokenCounter,
    CompressionStrategy,
    ConversationMemory,
)
from my_agent.infrastructure.memory.default_memory import DefaultConversationMemory
from my_agent.infrastructure.memory.token_counter import TransformersCounter
from my_agent.infrastructure.memory.compression import (
    LLMIncrementalCompression,
    RuleBasedPruning,
)

__all__ = [
    "Message",
    "TokenCounter",
    "CompressionStrategy",
    "ConversationMemory",
    "DefaultConversationMemory",
    "TransformersCounter",
    "LLMIncrementalCompression",
    "RuleBasedPruning",
]
