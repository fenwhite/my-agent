"""Orchestra 执行日志存储 - 将编排执行日志写入本地 JSON 文件。

将每次 Orchestra 执行的完整调用链写入 logs/orchestra/{session_id}.json，
包括用户输入、DAG 规划、每个 Agent 的输入/输出/状态/耗时。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from my_agent.infrastructure.repositories.chat_storage import ChatStorageIterface
from my_agent.utils.logging import get_logger

logger = get_logger(__name__)


class OrchestraLogStorage(ChatStorageIterface):
    """Orchestra 执行日志存储。

    将每次编排执行的完整调用链写入 `logs/orchestra/{session_id}.json`。

    该类实现了 :class:`ChatStorageInterface`，底层 JSON 读写统一收敛到接口方法
    （``save_session`` / ``load_session`` / ``clear_session`` /
    ``export_turn_full_prompt``）。

    Attributes:
        log_dir: 日志目录路径
    """

    def __init__(self, log_dir: str = "./logs/orchestra") -> None:
        """初始化日志存储。

        Args:
            log_dir: 日志目录路径
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, session_id: str, session_data: dict[str, Any]) -> None:
        """保存完整会话数据到 JSON 文件。

        Args:
            session_id: 会话唯一标识
            session_data: 包含 system_prompt、turns、metadata 的完整会话数据，
                或 Orchestra 执行日志数据
        """
        file_path = self.log_dir / f"{session_id}.json"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Orchestra 执行日志已保存到 {file_path}")
        except Exception as e:
            logger.error(f"保存 Orchestra 日志失败: {e}")

    def load_session(self, session_id: str) -> dict[str, Any] | None:
        """加载完整会话数据。

        Args:
            session_id: 会话唯一标识

        Returns:
            会话数据字典，如果不存在则返回 None
        """
        file_path = self.log_dir / f"{session_id}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载 Orchestra 日志失败: {e}")
            return None

    def clear_session(self, session_id: str) -> None:
        """删除指定会话的日志文件。

        Args:
            session_id: 会话唯一标识
        """
        file_path = self.log_dir / f"{session_id}.json"

        if not file_path.exists():
            return

        try:
            file_path.unlink()
            logger.info(f"Orchestra 会话 {session_id} 日志已清空")
        except Exception as e:
            logger.error(f"清空 Orchestra 日志失败: {e}")

    def export_turn_full_prompt(self, session_id: str, turn_index: int) -> dict[str, Any] | None:
        """导出指定轮次的完整 Prompt 上下文。

        对于 Orchestra 日志，"轮次"对应一次 Agent 执行记录（execution_logs 中的一条）。
        导出的 messages 由该次执行的输入/输出重构而成。

        Args:
            session_id: 会话唯一标识
            turn_index: 目标轮次索引（从 0 开始），对应 execution_logs 的下标

        Returns:
            包含完整 messages 数组的结构化数据，如果不存在则返回 None
        """
        session_data = self.load_session(session_id)
        if not session_data:
            return None

        execution_logs = session_data.get("execution_logs", [])
        if turn_index < 0 or turn_index >= len(execution_logs):
            logger.warning(f"无效的轮次索引: {turn_index}, 总执行记录数: {len(execution_logs)}")
            return None

        target_log = execution_logs[turn_index]

        messages: list[dict[str, str]] = [
            {"role": "system", "content": session_data.get("global_goal", "")},
            {
                "role": "user",
                "content": json.dumps(target_log.get("inputs", {}), ensure_ascii=False),
            },
            {
                "role": "assistant",
                "content": json.dumps(target_log.get("outputs", {}), ensure_ascii=False),
            },
        ]

        return {
            "session_id": session_id,
            "turn_index": turn_index,
            "messages": messages,
        }
