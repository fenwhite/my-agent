"""Orchestrator - 编排器主入口."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from my_agent.config.settings import get_settings
from my_agent.core.orchestra.blackboard import Blackboard
from my_agent.core.orchestra.executor import Executor
from my_agent.core.orchestra.planner import Planner, PlannerError
from my_agent.core.orchestra.scheduler import ScheduleResult, Scheduler
from my_agent.core.orchestra.state import OrchestraState, TaskNode
from my_agent.core.tools.executor import ToolExecutor
from my_agent.infrastructure.llm.sync_client import SyncLLMClient
from my_agent.infrastructure.repositories.orchestra_log_storage import OrchestraLogStorage
from my_agent.utils.logging import get_logger

logger = get_logger(__name__)


class OrchestraResult:
    """编排执行结果。
    
    Attributes:
        success: 是否成功
        state: 编排状态
        error: 错误信息（如果有）
    """
    def __init__(self, success: bool, state: OrchestraState, error: str = ""):
        self.success = success
        self.state = state
        self.error = error


class Orchestrator:
    """Orchestrator 编排器，串联 Planner → Scheduler → Executor 全流程。
    
    负责：
    1. 初始化执行状态
    2. 调用 Planner 生成 DAG
    3. 循环调用 Scheduler 选择任务并执行
    4. 管理重试逻辑
    5. 结束清理
    """

    def __init__(
        self, 
        llm_client: SyncLLMClient,
        tool_executor: ToolExecutor | None = None,
    ) -> None:
        """初始化 Orchestrator。
        
        Args:
            llm_client: LLM 客户端
            tool_executor: 工具执行器（可选，默认创建）
        """
        self._llm_client = llm_client
        self._tool_executor = tool_executor or ToolExecutor()
        
        self._planner = Planner(llm_client)
        self._executor = Executor(self._tool_executor)

    async def run(self, user_request: str) -> OrchestraResult:
        """执行完整编排流程。
        
        Args:
            user_request: 用户的请求
            
        Returns:
            编排执行结果
        """
        settings = get_settings()
        max_retries = settings.orchestra_max_retries
        
        logger.info(f"Orchestrator 开始执行: {user_request[:100]}...")
        
        # 1. 初始化状态
        state = OrchestraState(global_goal=user_request)
        state.blackboard = Blackboard()
        
        # 初始化日志存储
        log_storage = OrchestraLogStorage(log_dir=settings.orchestra_log_dir)
        
        try:
            # 2. Planner 生成 DAG
            tasks = self._planner.plan(user_request)
            self._build_task_dag(state, tasks)
            
            logger.info(f"任务 DAG 已生成，共 {len(state.task_dag)} 个任务")
            
            # 3. 循环调度执行
            await self._execution_loop(state, max_retries)
            
            # 4. 结束清理
            state.finished_at = datetime.now().isoformat()
            
            # 5. 保存执行日志
            log_storage.save(state)
            
            # 检查是否有任务失败
            has_failed = any(
                node.status == "FAILED" 
                for node in state.task_dag.values()
            )
            
            if has_failed:
                failed_tasks = [
                    tid for tid, node in state.task_dag.items()
                    if node.status == "FAILED"
                ]
                return OrchestraResult(
                    success=False,
                    state=state,
                    error=f"部分任务失败: {', '.join(failed_tasks)}",
                )
            
            return OrchestraResult(success=True, state=state)
            
        except PlannerError as e:
            logger.error(f"Planner 错误: {e}")
            state.finished_at = datetime.now().isoformat()
            log_storage.save(state)
            return OrchestraResult(success=False, state=state, error=str(e))
            
        except Exception as e:
            logger.error(f"Orchestrator 执行失败: {e}")
            state.finished_at = datetime.now().isoformat()
            log_storage.save(state)
            return OrchestraResult(success=False, state=state, error=str(e))

    def _build_task_dag(
        self, 
        state: OrchestraState, 
        tasks: list[dict[str, Any]]
    ) -> None:
        """构建任务 DAG。
        
        Args:
            state: 编排状态
            tasks: 任务列表
        """
        for task_data in tasks:
            task_id = task_data["task_id"]
            node = TaskNode(
                task_id=task_id,
                agent=task_data["agent"],
                depends_on=task_data.get("depends_on", []),
                parameters=task_data.get("parameters", {}),
            )
            state.task_dag[task_id] = node
            state.retry_counters[task_id] = 0

    async def _execution_loop(
        self, 
        state: OrchestraState, 
        max_retries: int
    ) -> None:
        """执行循环：Scheduler → Executor。
        
        Args:
            state: 编排状态
            max_retries: 最大重试次数
        """
        max_iterations = len(state.task_dag) * (max_retries + 1) + 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Scheduler 选择任务
            schedule = Scheduler.schedule(state.task_dag)
            
            if schedule.result == ScheduleResult.END:
                logger.info("所有任务已完成")
                break
            
            if schedule.result == ScheduleResult.DEADLOCK:
                # 尝试 Self-Correction：将失败任务重置为 PENDING 并重试
                if not await self._attempt_self_correction(state, max_retries):
                    logger.error("检测到死锁且无法恢复")
                    break
            
            # Executor 执行任务
            if schedule.task:
                task = schedule.task
                log = await self._executor.execute(task, state.blackboard)
                state.execution_logs.append(log)

    async def _attempt_self_correction(
        self,
        state: OrchestraState,
        max_retries: int,
    ) -> bool:
        """尝试 Self-Correction：重置失败任务并重试。
        
        根据 retry_counters 控制最大重试轮次。
        
        Args:
            state: 编排状态
            max_retries: 最大重试次数
            
        Returns:
            是否成功恢复
        """
        recovered = False
        
        for task_id, node in state.task_dag.items():
            if node.status == "FAILED":
                retry_count = state.retry_counters.get(task_id, 0)
                if retry_count < max_retries:
                    # 重置任务状态
                    node.status = "PENDING"
                    node.started_at = None
                    node.finished_at = None
                    state.retry_counters[task_id] = retry_count + 1
                    recovered = True
                    logger.info(
                        f"Self-Correction: 重置任务 {task_id} "
                        f"(重试 {retry_count + 1}/{max_retries})"
                    )
        
        return recovered
