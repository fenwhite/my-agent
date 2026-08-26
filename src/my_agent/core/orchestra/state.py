from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

@dataclass
class TaskNode:
    task_id: str
    agent: str
    depends_in: list[str]
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
    blackborad: Optional[Any] = None
    execution_logs: list[AgentExecutingLog] = field(default_factory=list)
    retry_counters: dict[str, int] = field(default_factory=dict)
    create_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None