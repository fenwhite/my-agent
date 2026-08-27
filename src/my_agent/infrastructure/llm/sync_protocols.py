"""Synchronous LLM client protocol."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam


class SyncLLMClientProtocol(Protocol):
    """协议：所有同步 LLM 客户端实现必须满足的接口契约。

    包含两个方法：
    - ``chat_completion()``：发送非流式聊天完成请求
    - ``get_response_content()``：从响应中提取文本内容
    """

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
        ...

    def get_response_content(self, response: ChatCompletion) -> str:
        """从 ChatCompletion 对象中提取文本内容。

        Args:
            response: ChatCompletion 对象

        Returns:
            AI 回复的文本内容
        """
        ...
