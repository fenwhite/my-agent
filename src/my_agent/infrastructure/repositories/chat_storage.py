
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ChatStorageInterface(ABC):
    """聊天存储接口，支持会话持久化。"""

    @abstractmethod
    def save_session(self, session_id: str, session_data: dict[str, Any]) -> None:
        """保存完整会话数据。

        Args:
            session_id: 会话唯一标识
            session_data: 包含 system_prompt、turns、metadata 的完整会话数据
        """
        pass

    @abstractmethod
    def load_session(self, session_id: str) -> dict[str, Any] | None:
        """加载完整会话数据。

        Args:
            session_id: 会话唯一标识

        Returns:
            包含 system_prompt、turns、metadata 的会话数据字典，如果不存在则返回 None
        """
        pass

    @abstractmethod
    def clear_session(self, session_id: str) -> None:
        """清空指定会话的历史记录。

        Args:
            session_id: 会话唯一标识
        """
        pass

    @abstractmethod
    def export_turn_full_prompt(self, session_id: str, turn_index: int) -> dict[str, Any] | None:
        """导出指定轮次的完整 Prompt 上下文。

        Args:
            session_id: 会话唯一标识
            turn_index: 目标轮次索引（从 0 开始）

        Returns:
            包含完整 messages 数组的结构化数据，如果不存在则返回 None
        """
        pass
