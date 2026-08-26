import json
from rich.console import Console
from rich.prompt import Confirm

from rag_agent.core.tools.tool_registry import ToolRegistry
from rag_agent.core.tools.hooks import HookRegistry, ToolExecutionContext
from rag_agent.core.tools.security import FileSecurityChecker
from rag_agent.utils.logging import get_logger
from rag_agent.config.settings import get_settings

logger = get_logger(__name__)

class ToolExecutionResult:
    def __init__(self, success: bool, output: str, error: str = ""):
        self.success = success
        self.output = output
        self.error = error

class ToolExecutor:
    def __init__(self, console: Console | None = None):
        self.registry = ToolRegistry.get_instance()
        self.hook_registry = HookRegistry.get_instance()
        self.console = console or Console()

        settings = get_settings()
        self.security_checker = FileSecurityChecker(
            whitelist_dirs=settings.tool_file_whitelist
        )

    async def execute_tool_call(self, tool_call: dict)-> ToolExecutionResult:
        tool_name = tool_call["name"]
        arguments = tool_call["arguments"]
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return ToolExecutionResult(
                    success=False,
                    output="",
                    error=f"参数解析失败: {arguments}"
                )

        tool_def = self.registry.get_tool(tool_name)
        if not tool_def:
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"未知工具: {tool_name}"
            )
        
        allowed, message = self._check_security(tool_name, arguments)
        if not allowed:
            if not await self._request_user_confirmation(message):
                return ToolExecutionResult(
                    success=False,
                    output="",
                    error="用户拒绝了操作"
                )
            
        pre_context = ToolExecutionContext(
            tool_name=tool_name,
            arguments=arguments,
            result=None
        )
        await self.hook_registry.execute_pre_hooks(pre_context)

        try:
            result = await tool_def.handler(**arguments)

            temp_files = []
            if isinstance(result, dict) and "file_id" in result:
                from rag_agent.core.tools.pagination import get_pagination_manager
                pagination_mgr = get_pagination_manager()
                file_path = str(pagination_mgr.get_temp_file_path(result["file_id"]))
                temp_files.append(file_path)

            post_context = ToolExecutionContext(
                tool_name=tool_name,
                arguments=arguments,
                result=result if isinstance(result, dict) else {"output": str(result)},
                temp_files_created=temp_files
            )

            await self.hook_registry.execute_post_hooks(post_context)

            return ToolExecutionResult(
                success=True,
                output=str(result)
            )
        except Exception as e:
            logger.error(f"工具执行失败: {e}")
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"工具执行失败: {e}"
            )



    def _check_security(self, tool_name: str, arguments: dict) -> tuple[bool, str]:
        if tool_name in ["locate_code", "read_code_window"]:
            return self.security_checker.check_read_access(arguments["file_path"])
        elif tool_name in ["write_file", "patch_code_window"]:
            return self.security_checker.check_write_access(arguments["file_path"])
        
        return True, ""

    async def _request_user_confirmation(self, message: str) -> bool:
        self.console.print(f"\n⚠[yellow]安全提示：[/yellow]\n{message}")
        return Confirm.ask("是否继续？", default=False)