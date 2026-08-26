from __future__ import annotations

from my_agent.core.orchestra.state import TaskNode

from my_agent.utils.logging import get_logger

logger = get_logger(__name__)

class ScheduleResult:
    TASK = "TASK"
    END = "END"
    DEADLOCK = "DEADLOCK"

class ScheduleOutput:
    def __init__(self, result: str, task: TaskNode):
        self.result = result
        self.task = task

class Scheduler:
    @staticmethod
    def schedule(task_dag: dict[str, TaskNode]) -> ScheduleOutput:
        if not task_dag:
            return ScheduleOutput(ScheduleResult.END, None)

        all_complete = all(
            node.status in ("SUCCESS", "FAILED") for node in task_dag.values()
        )
        if all_complete:
            return ScheduleOutput(ScheduleResult.END, None)

        ready_task = Scheduler._find_ready_task(task_dag)

        if ready_task is None:
            if Scheduler._has_deadlock(task_dag):
                logger.warning("Deadlock detected in task DAG.")
                return ScheduleOutput(ScheduleResult.DEADLOCK, None)
            return ScheduleOutput(ScheduleResult.END, None)

        return ScheduleOutput(ScheduleResult.TASK, ready_task)
        


    @staticmethod
    def  _find_ready_task(task_dag: dict[str, TaskNode]) -> TaskNode | None:
        for node in task_dag.items():
            if node.status != "PENDING":
                continue
            deps_satisfied = all(
                task_dag[dep_id].status == "SUCCESS"
                for dep_id in node.depends_on
                if dep_id in task_dag
            )

            if deps_satisfied:
                return node
        return None

    @staticmethod
    def _has_deadlock(task_dag: dict[str, TaskNode]) -> bool:
        pending_tasks = {
            tid: node for tid, node in task_dag.items()
            if node.status == "PENDING"
        }

        if not pending_tasks:
            return False

        for node in pending_tasks.items():
            deps_satisfied = all(
                task_dag[dep_id].status == "SUCCESS"
                for dep_id in node.depends_on
                if dep_id in task_dag
            )

            if deps_satisfied:
                return False

        for node in pending_tasks.items():
            for dep_id in node.depends_on:
                for dep_id in node.depends_on:
                    if dep_id in task_dag and task_dag[dep_id].status == "PENDING":
                        return True

        return False