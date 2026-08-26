from __future__ import annotations

import threading
from typing import Optional

from my_agent.core.orchestra.agent import SubAgent, AgentCapability
from my_agent.utils.logging import get_logger

logger = get_logger(__name__)

class AgentRegistry:
    _instance: Optional[AgentRegistry] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        if AgentRegistry._instance is not None:
            raise Exception("This class is a singleton, plz use get_instance() method to get the instance.")
        
        self._agents: dict[str, SubAgent] = {}

    @classmethod
    def get_instance(cls) -> AgentRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = AgentRegistry()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def register(self, agent: SubAgent) -> None:
        capability_name = agent.capability.name
        if capability_name in self._agents:
            logger.warning(f"Agent with capability '{capability_name}' is already registered. Overwriting.")

        self._agents[capability_name] = agent
        logger.info(f"Registered agent with capability '{capability_name}'.")

    def get_agent(self, capability_name: str) -> Optional[SubAgent]:
        agent = self._agents.get(capability_name)
        if agent is None:
            logger.warning(f"No agent found with capability '{capability_name}'.")
        return agent

    def get_capability_map(self) -> dict[str, AgentCapability]:
        return {name: agent.capability for name, agent in self._agents.items()}

    def get_agent_tools(self, agent_name: str) -> list[str]:
        agent = self._agents.get(agent_name)
        if agent is None:
            logger.warning(f"No agent found with capability '{agent_name}'.")
            return []
        return agent.capability.private_tools