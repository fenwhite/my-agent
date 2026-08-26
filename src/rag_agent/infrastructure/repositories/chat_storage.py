
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

class ChatStorageIterface(ABC):

    @abstractmethod
    def save_session(self, session_id: str, history: list[dict[str, Any]]) -> None:
        """保存会话历史

        Args:
            session_id  会话唯一标识
            history     对话历史记录列表
        """
        pass
    
    @abstractmethod
    def load_session(self,  session_id: str) -> list[dict[str, Any]] | None:
        """加载会话历史

        Args:
            session_id  会话唯一标识
        """
        pass

    @abstractmethod
    def clear_session(self,  session_id: str) -> None:
        """清除会话历史

        Args:
            session_id  会话唯一标识
        """
        pass