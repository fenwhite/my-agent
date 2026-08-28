"""默认对话记忆管理器实现。

提供基于 Token 预算的滑动窗口、实时压缩和跨会话恢复能力。
"""

from __future__ import annotations

from typing import Any

from my_agent.infrastructure.llm.sync_protocols import SyncLLMClientProtocol
from my_agent.infrastructure.memory.interfaces import (
    CompressionStrategy,
    ConversationMemory,
    Message,
    TokenCounter,
)
from my_agent.infrastructure.memory.token_counter import TransformersCounter
from my_agent.infrastructure.memory.compression import (
    LLMIncrementalCompression,
    RuleBasedPruning,
)
from my_agent.utils.logging import get_logger

logger = get_logger(__name__)


class DefaultConversationMemory:
    """默认对话记忆管理器实现。
    
    管理多轮对话的上下文，支持：
    - 基于 Token 预算的滑动窗口
    - 实时增量压缩（当超过水位线阈值时）
    - Tool Call 保护（注释中说明异步场景限制）
    - 跨会话状态恢复
    
    Attributes:
        token_counter: Token 计数器实例
        compression_strategy: 压缩策略实例
        token_budget: Token 预算上限
        waterline_ratio: 水位线阈值比例（0.8 表示 80%）
        system_prompt: 系统提示词
        compressed_summary: 当前的压缩摘要
        active_window: 活动窗口中的消息列表
        pending_tool_calls: 待完成的工具调用列表（当前未使用，预留字段）
    """
    
    def __init__(
        self,
        llm_client: SyncLLMClientProtocol,
        token_budget: int = 4000,
        waterline_ratio: float = 0.8,
        system_prompt: str = "",
        model_name: str = "Qwen/Qwen-7B-Chat",
    ) -> None:
        """初始化记忆管理器。
        
        Args:
            llm_client: LLM 客户端实例（用于压缩）
            token_budget: Token 预算上限
            waterline_ratio: 水位线阈值比例（0.0-1.0）
            system_prompt: 系统提示词
            model_name: Tokenizer 模型名称
            
        Note:
            关于异步 Tool Call 的限制说明：
            当前实现假设 Tool Call 是同步完成的（即在单次 LLM 调用内完成），
            不进行严格的配对检查。如果未来需要支持异步工具调用（即 Tool Call
            和 Tool Response 分布在不同的 LLM 调用中），需要增强保护逻辑，
            确保滑动窗口不会切断未完成的调用链。
        """
        self.token_counter: TokenCounter = TransformersCounter(model_name=model_name)
        self.compression_strategy: CompressionStrategy = LLMIncrementalCompression(llm_client)
        self.pruning_strategy = RuleBasedPruning()
        
        self.token_budget = token_budget
        self.waterline_ratio = waterline_ratio
        self.system_prompt = system_prompt
        
        # 状态
        self.compressed_summary = ""
        self.active_window: list[Message] = []
        self.pending_tool_calls: list[dict[str, Any]] = []  # 预留字段，当前未使用
        
        logger.info(
            f"记忆管理器已初始化: token_budget={token_budget}, "
            f"waterline={waterline_ratio}"
        )
    
    @property
    def compressed_summary(self) -> str:
        """获取当前的压缩摘要。"""
        return self._compressed_summary
    
    @compressed_summary.setter
    def compressed_summary(self, value: str) -> None:
        """设置压缩摘要。"""
        self._compressed_summary = value
    
    @property
    def active_window(self) -> list[Message]:
        """获取活动窗口中的消息列表。"""
        return self._active_window
    
    @active_window.setter
    def active_window(self, value: list[Message]) -> None:
        """设置活动窗口。"""
        self._active_window = value
    
    def add_message(self, message: Message) -> None:
        """添加一条新消息到记忆中。
        
        如果超过 Token 预算的水位线阈值，会自动触发压缩。
        
        Args:
            message: 要添加的消息
        """
        # 先修剪低价值内容（如过长的工具输出）
        pruned_message = self.pruning_strategy.prune([message])[0]
        
        # 添加到活动窗口
        self.active_window.append(pruned_message)
        
        # 检查是否需要压缩
        self._check_and_compress()
    
    def get_context_messages(self) -> list[Message]:
        """获取用于 LLM 调用的上下文消息列表。
        
        Returns:
            包含系统提示、压缩摘要和活动窗口的消息列表
        """
        messages = []
        
        # 添加系统提示
        if self.system_prompt:
            messages.append(Message(role="system", content=self.system_prompt))
        
        # 如果有压缩摘要，添加为特殊消息
        if self.compressed_summary:
            summary_message = Message(
                role="system",
                content=f"[历史对话摘要]\n{self.compressed_summary}",
            )
            messages.append(summary_message)
        
        # 添加活动窗口中的消息
        messages.extend(self.active_window)
        
        return messages
    
    def clear(self) -> None:
        """清空所有记忆数据。"""
        self.compressed_summary = ""
        self.active_window = []
        self.pending_tool_calls = []
        logger.info("记忆已清空")
    
    def load_state(
        self, compressed_summary: str, active_window: list[Message]
    ) -> None:
        """从持久化存储加载状态。
        
        Args:
            compressed_summary: 压缩摘要
            active_window: 活动窗口消息列表
        """
        self.compressed_summary = compressed_summary
        self.active_window = active_window
        logger.info(
            f"状态已加载: 摘要长度={len(compressed_summary)}, "
            f"活动窗口={len(active_window)} 条消息"
        )
    
    def get_state(self) -> tuple[str, list[Message]]:
        """获取当前状态以便持久化。
        
        Returns:
            (compressed_summary, active_window) 元组
        """
        return self.compressed_summary, self.active_window
    
    def _check_and_compress(self) -> None:
        """检查 Token 使用量，如果超过水位线则触发压缩。"""
        current_tokens = self.token_counter.count_messages_tokens(
            self.active_window
        )
        threshold = self.token_budget * self.waterline_ratio
        
        if current_tokens > threshold:
            logger.info(
                f"Token 使用量 {current_tokens} 超过阈值 {threshold}，触发压缩"
            )
            self._compress()
    
    def _compress(self) -> None:
        """执行增量压缩。
        
        将活动窗口中的旧消息压缩到摘要中，保留最近的消息在活动窗口。
        """
        if len(self.active_window) <= 2:
            # 消息太少，不需要压缩
            return
        
        # 决定哪些消息要压缩，哪些保留在活动窗口
        # 策略：保留最后 2 条消息，压缩之前的所有消息
        messages_to_compress = self.active_window[:-2]
        messages_to_keep = self.active_window[-2:]
        
        if not messages_to_compress:
            return
        
        # 执行压缩
        try:
            new_summary = self.compression_strategy.compress(
                old_summary=self.compressed_summary,
                new_messages=messages_to_compress,
                token_budget=self.token_budget,
            )
            
            # 更新状态
            self.compressed_summary = new_summary
            self.active_window = messages_to_keep
            
            logger.info(
                f"压缩完成: {len(messages_to_compress)} 条消息已压缩到摘要，"
                f"保留 {len(messages_to_keep)} 条消息在活动窗口"
            )
            
        except Exception as e:
            logger.error(f"压缩失败: {e}，保持原状")
            # 降级：简单丢弃最旧的消息
            if len(self.active_window) > 2:
                self.active_window = self.active_window[-2:]
