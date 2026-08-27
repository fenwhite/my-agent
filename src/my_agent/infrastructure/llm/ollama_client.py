"""Ollama 同步 LLM 客户端实现。

基于 OpenAI 同步 SDK 调用本地 Ollama 服务（OpenAI 兼容 API）。
"""

from __future__ import annotations

from typing import Any, Sequence

from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from my_agent.infrastructure.llm.sync_protocols import SyncLLMClientProtocol


class OllamaClient(SyncLLMClientProtocol):
    """同步 LLM 客户端，通过 OpenAI 兼容 API 调用本地 Ollama 服务。

    构造时传入配置，支持灵活切换不同 Ollama 实例。
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str,
        timeout: float = 60.0,
    ) -> None:
        """初始化 Ollama 客户端。

        Args:
            api_key: API 密钥（Ollama 通常为空字符串）
            base_url: Ollama API 基础 URL（如 http://localhost:11434/v1）
            default_model: 默认模型名称（如 llama3）
            timeout: 请求超时时间（秒）
        """
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        self._model = default_model

    def chat_completion(
        self,
        messages: Sequence[ChatCompletionMessageParam],
        **kwargs: Any,
    ) -> ChatCompletion:
        """发送非流式聊天完成请求。

        Args:
            messages: OpenAI 格式的对话消息列表
            **kwargs: 额外参数（如 temperature, max_tokens）

        Returns:
            ChatCompletion 响应对象
        """
        response: ChatCompletion = self._client.chat.completions.create(
            model=self._model,
            messages=list(messages),
            stream=False,
            **kwargs,
        )
        return response

    def get_response_content(self, response: ChatCompletion) -> str:
        """从 ChatCompletion 对象中提取文本内容。

        Args:
            response: ChatCompletion 对象

        Returns:
            AI 回复的文本内容
        """
        if not response.choices:
            return ""

        message = response.choices[0].message
        return message.content or ""
