from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

@dataclass
class AgentCapability:
    name: str
    description: str
    private_tools: list[str]
    required_inputs: dict[str, str] = field(default_factory=dict)
    outputs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("AgentCapability name cannot be empty.")
        if not self.description:
            raise ValueError("AgentCapability description cannot be empty.")


class SubAgent:
    def __init__(self, capability: AgentCapability) -> None:
        self._capability = capability

    @property
    def capability(self) -> AgentCapability:
        """获取 Agent 能力声明。"""
        return self._capability

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the agent's task with the provided inputs.

        Args:
            inputs (dict[str, Any]): A dictionary containing the required inputs for the agent.

        Returns:
            dict[str, Any]: A dictionary containing the outputs produced by the agent.
        """
        raise NotImplementedError("Subclasses must implement the execute method.")