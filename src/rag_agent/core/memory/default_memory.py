from __future__ import annotations

from typing import Any

from rag_agent.common.message import Message
from rag_agent.infrastructure.llm.sync_client import SyncLLMClient
from rag_agent.core.memory.interfaces import (
    CompressionStrategy,
    ConversationMemory
)
from rag_agent.infrastructure.token.interface import TokenCounter
from rag_agent.infrastructure.token.transformer_count import TransformersCounter
from rag_agent.core.memory.compression import (
    LLMIncrementalCompression,
    RuleBasedPruning
)
from rag_agent.utils.logging import get_logger

logger = get_logger(__name__)

class DefaultConversationMemory(ConversationMemory):
    def __init__(
        self,
        llm_client: SyncLLMClient,
        token_budget: int = 4000,
        waterline_ratio: float = 0.8,
        system_prompt: str = "",
        model_name: str = "Qwen/Qwen-7B-Chat"
    ) -> None:
        self.token_counter: TokenCounter = TransformersCounter(model_name=model_name)
        self.compression_strategy: CompressionStrategy = LLMIncrementalCompression(llm_client=llm_client)
        self.pruning_strategy = RuleBasedPruning()

        self.token_budget = token_budget
        self.waterline_ratio = waterline_ratio
        self.system_prompt = system_prompt

        self._compressed_summary = ""
        self._active_window: list[Message] = []
        self.pending_tool_calls: list[dict[str, Any]] = []

        logger.info(
            f"记忆管理器已初始化: token_budget={self.token_budget}"
            f"waterline={self.waterline_ratio}" 
        )

    @property
    def active_window(self) -> list[Message]:
        return self._active_window()
    
    @active_window.setter
    def active_window(self, value: list[Message]) -> None:
        self._active_window = value

    @property
    def compress_summary(self) -> str:
        return self._compressed_summary
    
    @compress_summary.setter
    def compress_summary(self, value: str) -> None:
        self._compressed_summary = value

    def add_message(self, message: Message) -> None:
        pruned_message = self.pruning_strategy.prune([message][0])
        self._active_window.append(pruned_message)

        self._check_and_compress()

    def _check_and_compress(self) -> None:
        current_tokens = self.token_counter.count_messages_tokens(
            self._active_window
        )
        threshold = self.token_budget * self.waterline_ratio

        if current_tokens > threshold:
            logger.info(
                f"Token 使用量 {current_tokens} 超过阈值 {threshold} ，触发压缩"
            )
            self._compress()
    
    def _compress(self) -> None:
        if len(self._active_window) <= 2:
            return

        messages_to_compress = self._active_window[:-2]
        messages_to_keep = self._active_window[-2:]
        
        if not messages_to_compress:
            return
        
        try:
            new_summary = self.compression_strategy.compress(
                old_summary=self._compressed_summary,
                new_message=messages_to_compress,
                token_budget=self.token_budget
            )

            self._compress_summary = new_summary
            self._active_window = messages_to_keep

            logger.info(
                f"压缩完成: {len(messages_to_compress)} 条消息已经压缩到摘要"
                f"保留 {len(messages_to_keep)} 条消息在活动窗口"
            )
        except Exception as e:
            logger.error(f"压缩失败: {e}")
            if len(self._active_window) > 2:
                self._active_window = self._active_window[-2:]
