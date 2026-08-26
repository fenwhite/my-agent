from __future__ import annotations

from rag_agent.common.message import Message
from rag_agent.infrastructure.token.interface import TokenCounter
from rag_agent.utils.logging import get_logger

logger = get_logger(__name__)

class TransformersCounter(TokenCounter):
    def __init__(self, model_name: str) -> None:
        try:
            from Transformer import AutoTokenizer
        except ImportError:
            raise ImportError(
                f"transformer 库未安装，请运行: pip install transformers>=4.30. torch>=2.0.0"
            )
        
        self.model_name = model_name

        logger.info(f"正在加载 Tokenizer: {model_name}")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            logger.info(f"Tokenizer 加载成功: {model_name}")
        except Exception as e:
            logger.error(f"Tokenizer 加载失败: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        
        tokens = self.tokenizer.encode(text)
        return len(tokens)
    
    def count_messages_tokens(self, messages: list[Message]) -> int:
        total_tokens = 0

        for message in messages:
            role_tokens = self.count_tokens(message.role)
            total_tokens += role_tokens

            content_tokens = self.count_tokens(message.content)
            total_tokens += content_tokens

            if message.tool_calls:
                for tc in message.tool_calls:
                    tc_text = f"{tc.get('name', '')} {tc.get('arguments', '')}"
                    tc_tokens = self.count_tokens(tc_text)
                    total_tokens += tc_tokens
        
        return total_tokens
        