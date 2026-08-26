from __future__ import annotations

import copy
from datetime import datetime
from typing import Any

from my_agent.core.orchestra.blackboard import Blackboard
from my_agent.core.orchestra.registry import AgentRegistry
from my_agent.core.orchestra.state import TaskNode, AgentExecutingLog
from my_agent.core.tools.executor import ToolExecutor
from my_agent.utils.logging import get_logger

logger = get_logger(__name__)

class Executor:

    def __init__(self, tool_exrcutor: ToolExecutor) -> None:
        self.tool_executor = tool_exrcutor
        self.agent_registry = AgentRegistry.get_instance()

    async def execute(self, task: TaskNode, blackboard: Blackboard) -> AgentExecutingLog:
        task_id = task.task_id
        agent_name = task.agent

        logger.info(f"Executing task {task_id} with agent {agent_name}")

        started_at = datetime.now().isoformat()
        task.status = "RUNNING"
        task.started_at = started_at

        agent = self.agent_registry.get_agent(agent_name)
        if not agent:
            error_msg = f"Agent '{agent_name}' not found."
            logger.error(error_msg)
            task.status = "FAILED"
            task.finished_at = datetime.now().isoformat()
            return AgentExecutingLog(
                task_id=task_id,
                agent=agent_name,
                status=task.status,
                inputs=task.parameters,
                outputs={},
                started_at=started_at,
                finished_at=task.finished_at,
                error=error_msg
            )

        inputs = self._filter_inputs(task, blackboard)

        try:
            outputs = await agent.execute(inputs)

            self._write_outputs(agent_name, outputs, blackboard)

            task.status = "SUCCESS"
            task.finished_at = datetime.now().isoformat()

            log = AgentExecutingLog(
                task_id=task_id,
                agent=agent_name,
                status="SUCCESS",
                inputs=inputs,
                outputs=outputs if isinstance(outputs, dict) else {"result": str(outputs)},
                started_at=started_at,
                finished_at=task.finished_at
            )

            logger.info(f"Task {task_id} executed successfully by agent {agent_name}.")
            return log
        except Exception as e:
            logger.error(f"Error executing task {task_id} with agent {agent_name}: {e}")
            task.status = "FAILED"
            task.finished_at = datetime.now().isoformat()
            error_msg = str(e)

            log = AgentExecutingLog(
                task_id=task_id,
                agent=agent_name,
                status="FAILED",
                inputs=inputs,
                outputs={},
                started_at=started_at,
                finished_at=task.finished_at,
                error=error_msg
            )

            logger.error(f"Task {task_id} execution failed by agent {agent_name}: {error_msg}")
            return log


    def _filter_inputs(self, task: TaskNode, blackboard: Blackboard) -> dict[str, Any]:
        agent = self._registry.get_agent(task.agent)

        inputs: dict[str, Any] = {}
        capability = agent.capability

        for key, value in task.parameters.items():
            if isinstance(value, str) and value.startswith("blackboard:"):
                ref_key = value[len("blackboard:"):]
                referenced_data = blackboard.read_by_key(ref_key)
                if referenced_data is not None:
                    inputs[key] = referenced_data
                else:
                    logger.warning(f"Referenced blackboard key '{ref_key}' not found for task {task.task_id}.")
                    inputs[key] = value
            else:
                inputs[key] = value

        for input_key in capability.private_inputs.items():
            if input_key not in inputs:
                pass

        return inputs

    def _write_outputs(self, agent_name: str, outputs: dict[str, Any], blackboard: Blackboard) -> None:
        if not isinstance(outputs, dict):
            return

        agent = self._registry.get_agent(agent_name)
        outputs_keys = agent.capability.output_keys if agent else []

        for key, value in outputs.items():
            if outputs_keys and key not in outputs_keys:
                continue
            blackboard.write(agent_name, key, value)

        logger.debug(f"Outputs from agent '{agent_name}' written to blackboard: {outputs}")