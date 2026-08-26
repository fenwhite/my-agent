from __future__ import annotations

import json
from typing import Any, Sequence

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from my_agent.core.orchestra.registry import AgentRegistry
from my_agent.core.services.prompt_registry import PromptRegistry
from my_agent.infrastructure.llm.sync_client import SyncLLMClient
from my_agent.utils.logging import get_logger

logger = get_logger(__name__)

class PlannerError(Exception):
    pass

class Planner:
    def __init__(self, llm_client: SyncLLMClient) -> None:
        self._llm_client = llm_client
        self._agent_registry = AgentRegistry.get_instance()
        self._prompt_registry = PromptRegistry.get_instance()

    def plan(self, user_input: str, context: dict[str, Any]) -> Sequence[dict[str, Any]]:
        agent_map = self._build_agent_map()
        if not agent_map:
            raise PlannerError("no agent map, can not do plan")

        system_prompt = self._build_system_prompt(agent_map=agent_map)
        user_message = f"请为以下任务生成规划: \n\n {user_input}"

        messages: Sequence[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        logger.info("Planner will invoke LLM to generate mission DAG ...")

        response = self._llm_client.char_completion(messages, temperature=0.1)
        content = self._llm_client.get_response_content(response)

        if not content:
            raise PlannerError("LLM return empty")

        tasks = self._parse_dag(content=content)

        self._validate_dag(tasks)

        logger.info(f"Planner generate the number of {len(tasks)} tasks")
        return tasks

        

    def _build_agent_map(self) -> str:
        capabilities = self._agent_registry.get_capability_map()

        lines: list[str] = []
        for name, cap in capabilities.items():
            lines.append(f"- **{name}**: {cap.description}")
            lines.append(f"  - 输入: {','.join(cap.required_inputs.keys()) if cap.required_inputs else '无'}")
            lines.append(f"  - 输出: {','.join(cap.outputs) if cap.outputs else '无'}")
            lines.append("")

        return "\n".join(lines)

    def _build_system_prompt(self, agent_map: str) -> str:
        try:
            system_prompt_template = self._prompt_registry.get("planner")
        except ValueError:
            logger.warning("Planner prompt not found in PromptRegistry. Using default template.")
            system_prompt_template = self._default_template()

        return system_prompt_template.replace("{agent_map}", agent_map)

    def _default_template(self) -> str:
        return (
            "你是一个任务规划器(Planner)， 负责将用户的复杂请求拆解为多个子任务"
            "可用的 Sub-Agent："
            "{agent_map}"
            "输出 JSON 数组， 每个元素包含 task_id, agent, depends_on, parameters."
        )

    def _parse_dag(self, content: str) -> list[dict[str, Any]] :
        text = content.strip()

        if text.startswith("```"):
            lines = text.split("\n")
            start = 1
            end = len(lines) - 1

            if lines[0].startswith("```"):
                start = 1
            if lines[-1].startswith("```"):
                end = len(lines) - 1

            text = "\n".join(lines[start:end]).strip()

        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "tasks" in data:
                return data["tasks"]
            raise PlannerError("LLM return with error format")
        except json.JSONDecodeError:
            pass

        start_idx = text.find("[")
        end_idx = text.find("]")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = text[start_idx:end_idx + 1]
            try:
                return json.load(json_str)
            except json.JSONDecodeError as e:
                raise PlannerError(f"DAG parse fail\n original text {content[:200]}")

        raise PlannerError(f"LLM parse fail\n original text {content[:200]}")

    def _validate_dag(self, tasks: list[dict[str, Any]]) -> None:
        if not tasks:
            raise PlannerError("DAG empty")

        all_agents = self._agent_registry.get_capability_map()
        task_ids = set()

        for i, task in enumerate(tasks):
            required_fields = ["task_id", "agent", "depends_on", "parameters"]
            for field in required_fields:
                if field not in task:
                    raise PlannerError(f"mission {i} lack of field {field}")

            task_id = task["task_id"]
            agent_name = task["agent"]
            depends_on = task["depends_on"]

            if task_id in task_ids:
                raise PlannerError(f"task_id repeat {task_id}")
            task_ids.add(task_id)

            if agent_name not in all_agents:
                raise PlannerError(f"Agent '{agent_name}' not available.")

            if not isinstance(depends_on, list):
                raise PlannerError(f"mission {task_id} needs depends_on field with list type")

            if not isinstance(task["parameters"], dict):
                raise PlannerError(f"mission {task_id} needs parameters field with dict type")

        for task in tasks:
            for dep in task["depends_on"]:
                if dep not in task_ids:
                    raise PlannerError(f"mission '{task_id}' depend on {dep} is not available")


    def _detect_cycle(self, tasks: list[dict[str, Any]], task_ids: set[str]) -> None:
        graph: dict[str, list[str]] = {}
        for task in tasks:
            graph[task["task_id"]] = list(task["depends_on"])

        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {tid : WHITE for tid in task_ids}

        def dfs(node: str) -> None:
            color[node] = GRAY
            for neighbor in graph.get(node, []):
                if color[neighbor] == GRAY:
                    raise PlannerError(f"found cycle of {node}")
                if color[neighbor] == WHITE:
                    dfs(neighbor)
            color[node] = BLACK

        for tid in task_ids:
            if color[tid] == WHITE:
                dfs(tid)