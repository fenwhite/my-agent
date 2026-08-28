"""对话压缩策略实现。

提供基于 LLM 的增量压缩和基于规则的修剪策略。
"""

from __future__ import annotations

from typing import Any

from my_agent.core.services.prompt_registry import PromptRegistry
from my_agent.infrastructure.llm.sync_client import SyncLLMClient
from my_agent.infrastructure.memory.interfaces import (
    CompressionStrategy,
    Message,
)
from my_agent.utils.logging import get_logger

logger = get_logger(__name__)


class LLMIncrementalCompression(CompressionStrategy):
    """基于 LLM 的增量压缩策略。
    
    使用 LLM 将旧摘要和新消息合并为新的精简摘要，
    保留核心信息并丢弃冗余内容。
    
    Attributes:
        llm_client: LLM 客户端实例
        prompt_template: 压缩提示词模板路径
    """
    
    def __init__(
        self,
        llm_client: SyncLLMClient,
        prompt_template: str = "memory_compression.md",
    ) -> None:
        """初始化压缩策略。
        
        Args:
            llm_client: LLM 客户端实例
            prompt_template: 压缩提示词模板名称（在 prompts/ 目录下）
        """
        self.llm_client = llm_client
        self.prompt_template = prompt_template
    
    def compress(
        self,
        old_summary: str,
        new_messages: list[Message],
        token_budget: int,
    ) -> str:
        """增量压缩对话历史。
        
        使用 LLM 将旧摘要和新消息合并为新的精简摘要。
        
        Args:
            old_summary: 之前的压缩摘要（首次压缩时为空字符串）
            new_messages: 新增的消息列表
            token_budget: Token 预算上限
            
        Returns:
            压缩后的摘要文本
        """
        if not new_messages:
            return old_summary
        
        # 格式化新消息
        messages_text = self._format_messages(new_messages)
        
        # 加载压缩提示词
        registry = PromptRegistry.get_instance()
        try:
            prompt_template = registry.get(self.prompt_template)
        except (ValueError, KeyError):
            logger.warning(f"压缩提示词文件 {self.prompt_template} 不存在，使用默认模板")
            prompt_template = self._get_default_compression_prompt()
        
        # 填充提示词（适配 memory_compression.md 的占位符）
        if "{new_turns}" in prompt_template:
            # 使用原始 prompt 文件的占位符
            prompt = prompt_template.format(
                old_summary=old_summary or "无",
                new_turns=messages_text,
            )
        else:
            # 使用自定义占位符
            prompt = prompt_template.format(
                old_summary=old_summary or "无",
                new_messages=messages_text,
                token_budget=token_budget,
            )
        
        # 调用 LLM 进行压缩
        try:
            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )
            compressed = self.llm_client.get_response_content(response)
            
            logger.info(
                f"压缩完成: {len(new_messages)} 条消息 -> {len(compressed)} 字符"
            )
            return compressed
            
        except Exception as e:
            logger.error(f"LLM 压缩失败: {e}，返回旧摘要")
            # 降级：返回旧摘要或截断新消息
            if old_summary:
                return old_summary
            else:
                # 如果没有旧摘要，简单截断新消息
                return self._truncate_messages(new_messages, token_budget)
    
    def _format_messages(self, messages: list[Message]) -> str:
        """格式化消息列表为文本。
        
        Args:
            messages: 消息列表
            
        Returns:
            格式化后的文本
        """
        parts = []
        for msg in messages:
            role_label = {
                "user": "用户",
                "assistant": "助手",
                "system": "系统",
                "tool": "工具",
            }.get(msg.role, msg.role)
            
            content = msg.content.strip()
            if content:
                parts.append(f"{role_label}: {content}")
            
            # 如果有工具调用，也包含进来
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get("name", "unknown")
                    args = tc.get("arguments", {})
                    parts.append(f"[工具调用] {tool_name}({args})")
        
        return "\n".join(parts)
    
    def _truncate_messages(
        self, messages: list[Message], token_budget: int
    ) -> str:
        """简单截断消息作为降级方案。
        
        Args:
            messages: 消息列表
            token_budget: Token 预算
            
        Returns:
            截断后的文本
        """
        # 只保留最后几条消息
        max_messages = min(len(messages), 3)
        truncated = messages[-max_messages:]
        return self._format_messages(truncated)
    
    def _get_default_compression_prompt(self) -> str:
        """获取默认的压缩提示词模板。
        
        Returns:
            默认提示词模板
        """
        return """你是一个专业的对话摘要助手。请将以下对话历史压缩为精简的摘要，保留关键信息。

**要求：**
1. 保留用户的核心问题和意图
2. 保留助手的关键回答和结论
3. 保留重要的事实信息和数据
4. 删除冗余的寒暄、重复内容和无关细节
5. 摘要长度控制在 {token_budget} Token 以内

**之前的摘要：**
{old_summary}

**新增对话：**
{new_messages}

**请输出压缩后的摘要：**"""


class RuleBasedPruning:
    """基于规则的修剪策略。
    
    通过规则移除低价值内容，如 Tool Output 过长时的截断。
    通常作为 LLM 压缩的前置步骤。
    """
    
    def __init__(self, max_tool_output_length: int = 500) -> None:
        """初始化修剪策略。
        
        Args:
            max_tool_output_length: 工具输出的最大长度（字符数）
        """
        self.max_tool_output_length = max_tool_output_length
    
    def prune(self, messages: list[Message]) -> list[Message]:
        """修剪消息列表中的低价值内容。
        
        主要处理：
        1. 过长的工具输出（截断并添加省略标记）
        2. 空消息
        
        Args:
            messages: 原始消息列表
            
        Returns:
            修剪后的消息列表
        """
        pruned = []
        
        for msg in messages:
            # 跳过空消息
            if not msg.content and not msg.tool_calls:
                continue
            
            # 处理工具输出过长的情况
            if msg.role == "tool" and len(msg.content) > self.max_tool_output_length:
                truncated = msg.content[: self.max_tool_output_length]
                pruned_content = (
                    f"{truncated}\n\n[... 输出过长，已截断 ...]"
                )
                pruned.append(
                    Message(
                        role=msg.role,
                        content=pruned_content,
                        tool_call_id=msg.tool_call_id,
                    )
                )
            else:
                pruned.append(msg)
        
        logger.info(f"修剪完成: {len(messages)} -> {len(pruned)} 条消息")
        return pruned
