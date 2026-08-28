"""Token 计数器实现。

提供基于 Transformers 库的精确 Token 计数功能。
"""

from __future__ import annotations

from typing import Any

from my_agent.infrastructure.memory.interfaces import Message, TokenCounter
from my_agent.utils.logging import get_logger

logger = get_logger(__name__)


class TransformersCounter(TokenCounter):
    """基于 Transformers Tokenizer 的 Token 计数器。
    
    使用 HuggingFace Transformers 库进行精确的 Token 计数，
    支持配置不同的模型 Tokenizer。
    
    Attributes:
        model_name: 模型名称，默认为 Qwen/Qwen-7B-Chat
        tokenizer: 已加载的 Tokenizer 实例
    """
    
    def __init__(self, model_name: str = "qwen/Qwen-7B-Chat") -> None:
        """初始化 Token 计数器。
        
        Args:
            model_name: 模型名称，用于加载对应的 Tokenizer
            
        Raises:
            ImportError: 如果 modelscope 或 torch 未安装
        """
        try:
            from modelscope import AutoTokenizer
        except ImportError:
            raise ImportError(
                "modelscope 库未安装，请运行: pip install modelscope>=1.9.0 torch>=2.0.0"
            )
        
        self.model_name = model_name
        logger.info(f"正在通过 ModelScope 加载 Tokenizer: {model_name}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, 
                trust_remote_code=True
            )
            logger.info(f"Tokenizer 加载成功: {model_name}")
        except Exception as e:
            logger.error(f"加载 Tokenizer 失败: {e}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """计算文本的 Token 数量。
        
        Args:
            text: 要计算的文本
            
        Returns:
            Token 数量
        """
        if not text:
            return 0
        
        tokens = self.tokenizer.encode(text)
        return len(tokens)
    
    def count_messages_tokens(self, messages: list[Message]) -> int:
        """计算消息列表的总 Token 数量。
        
        Args:
            messages: 消息列表
            
        Returns:
            总 Token 数量
        """
        total_tokens = 0
        
        for message in messages:
            # 计算 role 的 token
            role_tokens = self.count_tokens(message.role)
            total_tokens += role_tokens
            
            # 计算 content 的 token
            content_tokens = self.count_tokens(message.content)
            total_tokens += content_tokens
            
            # 如果有 tool_calls，也计算它们的 token
            if message.tool_calls:
                for tc in message.tool_calls:
                    tc_text = f"{tc.get('name', '')} {tc.get('arguments', '')}"
                    tc_tokens = self.count_tokens(tc_text)
                    total_tokens += tc_tokens
        
        return total_tokens
