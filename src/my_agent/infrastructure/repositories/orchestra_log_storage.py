"""Orchestra 执行日志存储 - 将编排执行日志写入本地 JSON 文件。

将每次 Orchestra 执行的完整调用链写入 logs/orchestra/{session_id}.json，
包括用户输入、DAG 规划、每个 Agent 的输入/输出/状态/耗时。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from my_agent.core.orchestra.state import AgentExecutingLog, OrchestraState
from my_agent.utils.logging import get_logger

logger = get_logger(__name__)


class OrchestraLogStorage:
    """Orchestra 执行日志存储。

    将每次编排执行的完整调用链写入 `logs/orchestra/{session_id}.json`。

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

    def save(self, state: OrchestraState) -> None:
        """保存编排执行日志到 JSON 文件。

        Args:
            state: 编排执行状态
        """
        file_path = self.log_dir / f"{state.session_id}.json"

        log_data = self._build_log_data(state)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Orchestra 执行日志已保存到 {file_path}")
        except Exception as e:
            logger.error(f"保存 Orchestra 日志失败: {e}")

    def load(self, session_id: str) -> dict[str, Any] | None:
        """加载编排执行日志。

        Args:
            session_id: 会话 ID

        Returns:
            日志数据，如果不存在则返回 None
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

    def _build_log_data(self, state: OrchestraState) -> dict[str, Any]:
        """构建日志数据。

        Args:
            state: 编排执行状态

        Returns:
            日志数据字典
        """
        # 构建任务 DAG 信息
        dag_info: list[dict[str, Any]] = []
        for task_id, node in state.task_dag.items():
            dag_info.append({
                "task_id": node.task_id,
                "agent": node.agent,
                "depends_on": node.depends_on,
                "parameters": node.parameters,
                "status": node.status,
                "started_at": node.started_at,
                "finished_at": node.finished_at,
            })

        # 构建执行日志列表
        execution_logs: list[dict[str, Any]] = []
        for log in state.execution_logs:
            execution_logs.append(self._log_to_dict(log))

        return {
            "session_id": state.session_id,
            "global_goal": state.global_goal,
            "created_at": state.created_at,
            "finished_at": state.finished_at,
            "task_dag": dag_info,
            "execution_logs": execution_logs,
        }

    @staticmethod
    def _log_to_dict(log: AgentExecutingLog) -> dict[str, Any]:
        """将 AgentExecutionLog 转为字典。

        Args:
            log: 执行日志

        Returns:
            字典格式
        """
        result: dict[str, Any] = {
            "task_id": log.task_id,
            "agent": log.agent,
            "status": log.status,
            "inputs": log.inputs,
            "outputs": log.outputs,
            "started_at": log.started_at,
            "finished_at": log.finished_at,
        }
        if log.error is not None:
            result["error"] = log.error
        return result
