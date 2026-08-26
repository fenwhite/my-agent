
from __future__ import annotations

from typing import Any, Sequence

from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from my_agent.config.settings import get_settings
from my_agent.utils.logging import get_logger

logger = get_logger(__name__)

class SyncLLMClient:
    def __init__(self,
                 api_key: str,
                 base_url: str,
                 default_model: str,
                 timeout: float = 60.0) -> None:
        self._client = OpenAI(
            api_key= api_key,
            base_url= base_url,
            timeout = timeout
        )
        self._model = default_model

    def chat_completion(
            self,
            messages: Sequence[ChatCompletionMessageParam],
            **kwargs: Any
    ) -> ChatCompletion:
        target_model = self._model

        response: ChatCompletion = self._client.chat.completions.create(
            model=target_model,
            messages=list(messages),
            stream=False,
            **kwargs
        )

        return response
    
    def get_response_content(self, response: ChatCompletion) -> str:
        if not response.choices:
            return ""
        
        message = response.choices[0].message
        return message.content or ""