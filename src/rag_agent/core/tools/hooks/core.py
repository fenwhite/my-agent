from typing import Callable, Awaitable, List
from dataclasses import dataclass, field

from rag_agent.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class ToolExecutionContext:
    tool_name: str
    arguments: dict
    result: dict | None = None
    temp_files_created: list[str] = field(default_factory=list)

ToolPreHook = Callable[[ToolExecutionContext], Awaitable[None]]
ToolPostHook = Callable[[ToolExecutionContext], Awaitable[None]]

class HookRegistry:
    _instance = None

    _global_pre_hooks: List[ToolPreHook] = []
    _tool_pre_hooks: dict[str, List[ToolPreHook]] = {}

    _global_post_hooks: List[ToolPostHook] = []
    _tool_post_hooks: dict[str, List[ToolPostHook]] = {}

    @classmethod
    def get_instance(cls) -> 'HookRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register_pre_hook(
        self,
        hook: ToolPreHook,
        tool_names: list[str] | None = None
    ):
        if tool_names is None:
            self._global_pre_hooks.append(hook)
            logger.info(f"已注册全局 Pre Hook: {hook.__name__}")
        else:
            for tool_name in tool_names:
                if tool_name not in self._tool_pre_hooks:
                    self._tool_pre_hooks[tool_name] = []
                self._tool_pre_hooks[tool_name].append(hook)
            logger.info(f"已注册工具级 Pre Hook: {hook.__name__} (tools={tool_names})")
    
    def register_post_hook(
        self,
        hook: ToolPostHook,
        tool_names: list[str] | None = None
    ):
        if tool_names is None:
            self._global_post_hooks.append(hook)
            logger.info(f"已注册全局 Post Hook: {hook.__name__}")
        else:
            for tool_name in tool_names:
                if tool_name not in self._tool_post_hooks:
                    self._tool_post_hooks[tool_name] = []
                self._tool_post_hooks[tool_name].append(hook)
            logger.info(f"已注册工具级 Post Hook: {hook.__name__} (tools={tool_names})")
    
    async def execute_pre_hooks(self, context: ToolExecutionContext):
        hooks_to_run = []

        hooks_to_run.extend(self._global_pre_hooks)

        if context.tool_name in self._tool_pre_hooks:
            hooks_to_run.extend(self._tool_pre_hooks[context.tool_name])

        for hook in hooks_to_run:
            try:
                await hook(context)
            except Exception as e:
                logger.error(f"Pre Hook 执行失败 [{hook.__name__}]: {e}")

    async def execute_post_hooks(self, context: ToolExecutionContext):
        hooks_to_run = []

        hooks_to_run.extend(self._global_post_hooks)

        if context.tool_name in self._tool_post_hooks:
            hooks_to_run.extend(self._tool_post_hooks[context.tool_name])

        for hook in hooks_to_run:
            try:
                await hook(context)
            except Exception as e:
                logger.error(f"Post Hook 执行失败 [{hook.__name__}]: {e}")