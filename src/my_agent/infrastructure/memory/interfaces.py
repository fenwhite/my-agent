"""对话记忆管理模块的接口定义。

本模块定义了对话记忆管理的核心接口，包括消息结构、Token 计数器、
压缩策略和记忆管理器。所有实现都应遵循这些接口规范。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Message:
    """单条对话消息。
    
    Attributes:
        role: 消息角色（system/user/assistant/tool）
        content: 消息内容
        tool_calls: 工具调用列表（仅 assistant 角色可能有）
        tool_call_id: 工具调用 ID（仅 tool 角色必须有）
    """
    role: str
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。"""
        result: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """从字典创建消息对象。"""
        return cls(
            role=data["role"],
            content=data.get("content", ""),
            tool_calls=data.get("tool_calls", []),
            tool_call_id=data.get("tool_call_id"),
        )


class TokenCounter(Protocol):
    """Token 计数器协议。
    
    用于精确计算文本的 Token 数量，支持不同模型的 Tokenizer。
    """
    
    def count_tokens(self, text: str) -> int:
        """计算文本的 Token 数量。
        
        Args:
            text: 要计算的文本
            
        Returns:
            Token 数量
        """
        ...
    
    def count_messages_tokens(self, messages: list[Message]) -> int:
        """计算消息列表的总 Token 数量。
        
        Args:
            messages: 消息列表
            
        Returns:
            总 Token 数量
        """
        ...


class CompressionStrategy(Protocol):
    """压缩策略协议。
    
    用于将长对话历史压缩为精简摘要，保留核心信息。
    """
    
    def compress(
        self,
        old_summary: str,
        new_messages: list[Message],
        token_budget: int,
    ) -> str:
        """增量压缩对话历史。
        
        Args:
            old_summary: 之前的压缩摘要（首次压缩时为空字符串）
            new_messages: 新增的消息列表
            token_budget: Token 预算上限
            
        Returns:
            压缩后的摘要文本
        """
        ...


class ConversationMemory(Protocol):
    """对话记忆管理器协议。
    
    管理多轮对话的上下文，支持滑动窗口、实时压缩和跨会话恢复。
    """
    
    @property
    def compressed_summary(self) -> str:
        """获取当前的压缩摘要。"""
        ...
    
    @property
    def active_window(self) -> list[Message]:
        """获取活动窗口中的消息列表。"""
        ...
    
    def add_message(self, message: Message) -> None:
        """添加一条新消息到记忆中。
        
        如果超过 Token 预算，会自动触发压缩。
        
        Args:
            message: 要添加的消息
        """
        ...
    
    def get_context_messages(self) -> list[Message]:
        """获取用于 LLM 调用的上下文消息列表。
        
        Returns:
            包含系统提示、压缩摘要和活动窗口的消息列表
        """
        ...
    
    def clear(self) -> None:
        """清空所有记忆数据。"""
        ...
    
    def load_state(self, compressed_summary: str, active_window: list[Message]) -> None:
        """从持久化存储加载状态。
        
        Args:
            compressed_summary: 压缩摘要
            active_window: 活动窗口消息列表
        """
        ...
    
    def get_state(self) -> tuple[str, list[Message]]:
        """获取当前状态以便持久化。
        
        Returns:
            (compressed_summary, active_window) 元组
        """
        ...
