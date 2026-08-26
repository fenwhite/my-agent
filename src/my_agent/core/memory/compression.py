from __future__ import annotations

from my_agent.common.message import Message
from my_agent.core.services.prompt_registry import PromptRegistry
from my_agent.infrastructure.llm.sync_client import SyncLLMClient
from my_agent.core.memory.interfaces import CompressionStrategy
from my_agent.utils.logging import get_logger

logger = get_logger(__name__)

class LLMIncrementalCompression(CompressionStrategy):
    def __init__(
        self,
        llm_client: SyncLLMClient,
        prompt_template: str = "memory_compression"
    ) -> None:
        self.llm_client = llm_client
        self.prompt_template = prompt_template    

    def compress(self, old_summary, new_message, token_budget) -> str:
        if not new_message:
            return old_summary
        
        messages_text = self._fomat_messages(new_message)

        registry = PromptRegistry.get_instance()
        try:
            prompt_template = registry.get(self.prompt_template)
        except (ValueError, KeyError):
            logger.warning(f"压缩提示词文件 {self.prompt_template} 不存在,使用默认模板")
            prompt_template = self._get_default_compression_propmt()
        
        if "{new_turns}" in prompt_template:
            prompt = prompt_template.format(
                old_summary=old_summary or "无",
                new_turns=messages_text
            )
        else:
            prompt = prompt_template.format(
                old_summary=old_summary or "无",
                new_turns=messages_text,
                token_budget=token_budget
            )

        try:
            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )
            compressed = self.llm_client.get_response_content(response)

            logger.info(
                f"压缩完成: {len(new_message)} 条消息 -> {len(compressed)} 字符"
            )

            return compressed
        except Exception as e:
            logger.error(F"LLM 压缩失败: {e}, 返回旧摘要")
            if old_summary:
                return old_summary
            else:
                return self._truncate_messages(new_message)

    def _fomat_messages(self, messages: list[Message]) -> str:
        parts = []
        for msg in messages:
            role_label = {
                "user": "用户",
                "assistant": "助手",
                "system": "系统",
                "tool": "工具"
            }.get(msg.role, msg.role)

            content = msg.content.strip()
            if content:
                parts.append(f"{role_label}: {content}")

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get("name", "unkown")
                    args = tc.get("arguments", {})
                    parts.append(f"[工具调用] {tool_name}({args})")
            
            return "\n".join(parts)
        
    def _truncate_messages(
            self,
            messages: list[Message]
    ) -> str:
        max_messages = min(len(messages), 3)
        truncated = messages[-max_messages:]
        return self._fomat_messages(truncated)
    
    def _get_default_compression_propmt(self) -> str:
        # TODO 获取默认压缩提示词模板
        return ""
    
class RuleBasedPruning:
    def __init__(self, max_tool_output_length: int = 500) -> None:
        self.max_tool_output_length = max_tool_output_length

    def prune(self, messages: list[Message]) -> list[Message]:
        pruned = []

        for msg in messages:
            if not msg.content and not msg.tool_calls:
                continue

            if msg.role == "tool" and len(msg.content) > self.max_tool_output_length:
                truncated = msg.content[: self.max_tool_output_length]
                pruned_content = (
                    f"{truncated}\n\n[...输出过长，已截断]"
                )

                pruned.append(Message(
                    role=msg.role,
                    content=pruned_content,
                    tool_call_id=msg.tool_call_id
                ))
            else:
                pruned.append(msg)
        
        logger.info(f"剪枝完成: {len(messages)} -> {len(pruned)} 条消息")
        return pruned