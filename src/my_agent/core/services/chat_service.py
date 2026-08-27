
from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, List
from datetime import datetime

from my_agent.core.services.prompt_registry import PromptRegistry
from my_agent.infrastructure.repositories.chat_storage import ChatStorageIterface
from my_agent.infrastructure.llm.sync_client import SyncLLMClient
from my_agent.infrastructure.repositories.json_chat_storage import JsonChatStorage
from my_agent.core.tools.executor import ToolExecutor
from my_agent.core.tools.tool_registry import ToolRegistry
from my_agent.utils.logging import get_logger

logger = get_logger(__name__)

class ChatService:

    def __init__(
        self,
        llm_client: SyncLLMClient,
        storage: ChatStorageIterface | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._storage = storage or JsonChatStorage()
        self._session_id = str(uuid.uuid4())
        self._system_prompt = ""
        self._turn_count = 0

        self._tool_executor = ToolExecutor()
        self._tool_registry = ToolRegistry.get_instance()

        self._max_tool_iterations = 10
        self._max_same_tool_calls = 3
        self._tool_call_history = List[dict] = []


    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def turn_count(self) -> int:
        return self._turn_count

    def chat(
        self,
        user_input: str,
        context_window: int = 10,
        max_turns: int = 20,
    ) -> dict[str, Any]:
        if self._turn_count >= max_turns:
            msg = "本轮对话已经达到长度限制，建议开启新会话以保持最佳性能"
            self._save_history()
            return {"content": msg, "tool_calls": [], "session_ended": True}

        if not self._system_prompt:
            prompt_registry = PromptRegistry.get_instance()
            self._system_prompt = prompt_registry.get_current()
        
        turn_data = {
            "turn_index": self._turn_count,
            "timestamp": datetime.now().isoformat(),
            "iterations": [],
            "added_messages"; [],
        }

        self._turn_count += 1

        self._tool_call_history = []

        context_messages = self._build_context(context_window)
        
        try:
            response = self._llm_client.chat_completion(messages=context_messages)
            ai_content = self._llm_client.get_response_content(response)
            tool_calls = self._extract_tool_calls(response)

            self._history.append({"role": "assistant", "content": ai_content})
            self._save_history()

            return {
                "content": ai_content,
                "tool_calls": tool_calls,
                "session_ended": False,
            }
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return {
                 "content": f"抱歉，处理您的请求时出现错误: {str(e)}",
                "tool_calls": [],
                "session_ended": False,
            }
    
    def _build_context(self, window_size: int) -> list[dict[str, str]]:
        recent_history = self._history[-(window_size * 2):]
        registry = PromptRegistry.get_instance()
        system_message = {
            "role": "system",
            "content": registry.get_current()
        }

        return [system_message] + recent_history

    def _extract_tool_calls(self, response) -> list[dict[str, Any]]:
        tool_calls = []
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            for tc in response.choices[0].message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name if hasattr(tc, function) else "unknown",
                    "arguments": tc.function.arguments if hasattr(tc, arguments) else "{}",
                })

        return tool_calls

    def _save_history(self):
        try:
            self._storage.save_session(self._session_id, self._history)
        except Exception as e:
            logger.warning(f"保存会话历史失败: {e}")

    def clear_history(self):
        self._history.clear()
        self._turn_count = 0
        self._storage.clear_session(self._session_id)
        self._session_id = str(uuid.uuid4())
        logger.info(f"新会话 {self._session_id} 已创建")