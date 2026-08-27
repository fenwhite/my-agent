from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from my_agent.core.orchestra.blackboard import Blackboard

@dataclass
class TaskNode:
    """DAG 中的任务节点。
    
    Attributes:
        task_id: 任务唯一标识
        agent: 执行该任务的 Agent 名称
        depends_on: 依赖的任务 ID 列表
        parameters: 传递给 Agent 的参数
        status: 任务状态 (PENDING/RUNNING/SUCCESS/FAILED/RETRY)
        started_at: 任务开始时间
        finished_at: 任务完成时间
    """
    task_id: str
    agent: str
    depends_on: list[str]
    parameters: dict[str, Any]
    status: str = "PENDING"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

@dataclass
class AgentExecutingLog:
    task_id: str
    agent: str
    status: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    started_at: str
    finished_at: str
    error: Optional[str] = None

@dataclass
class OrchestraState:
    global_goal: str
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_dag: dict[str, TaskNode] = field(default_factory=dict)
    blackboard: Optional[Blackboard] = None  # Blackboard 实例
    execution_logs: list[AgentExecutingLog] = field(default_factory=list)
    retry_counters: dict[str, int] = field(default_factory=dict)
    create_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None