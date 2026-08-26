from typing import Dict, List

from rag_agent.core.tools.definitions.base import ToolDefinition

class ToolRegistry:
    _instance = None
    _tools: Dict[str, ToolDefinition] = {}

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def registry(self, tool: ToolDefinition):
        self._tools[tool.name] = tool

    def register_multiple(self, tools: List[ToolDefinition]):
        for tool in tools:
            self.registry(tool)

    def get_tool(sefl, name: str) -> ToolDefinition:
        return sefl._tools.get(name)
    
    def get_all_tools(self) -> List[dict]:
        return list(self._tools.values())
    
    def get_openai_tools_format(self) -> List[dict]:
        return [tool.to_openai_format() for tool in self._tools.values()]