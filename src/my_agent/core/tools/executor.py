"""Tool executor with security checks and user confirmation."""

import json
from typing import Any
from rich.console import Console
from rich.prompt import Confirm

from my_agent.common.tool_names import READ_CODE_WINDOW, LOCATE_CODE, PATCH_CODE_WINDOW, CREATE_FILE
from my_agent.core.tools.tool_registry import ToolRegistry
from my_agent.core.tools.hooks import HookRegistry, ToolExecutionContext
from my_agent.core.tools.security import FileSecurityChecker
from my_agent.utils.logging import get_logger
from my_agent.config.settings import get_settings

logger = get_logger(__name__)


class ToolExecutionResult:
    """工具执行结果。"""
    def __init__(self, success: bool, output: str, error: str = ""):
        self.success = success
        self.output = output
        self.error = error


class ToolExecutor:
    """工具执行器。
    
    职责：
    1. 接收 LLM 返回的工具调用请求
    2. 执行安全检查（白名单 + 用户确认）
    3. 调用实际的工具处理函数
    4. 执行 Post Hooks（如临时文件清理）
    5. 返回执行结果
    """
    
    def __init__(self, console: Console | None = None):
        self.registry = ToolRegistry.get_instance()
        self.hook_registry = HookRegistry.get_instance()
        self.console = console or Console()
        
        # 从配置加载白名单
        settings = get_settings()
        self.security_checker = FileSecurityChecker(
            whitelist_dirs=settings.tool_file_whitelist
        )
    
    async def execute_tool_call(
        self, 
        tool_call: dict, 
        agent_name: str | None = None
    ) -> ToolExecutionResult:
        """执行单个工具调用。
        
        Args:
            tool_call: LLM 返回的工具调用信息
                      {"name": "read_file", "arguments": {...}}
            agent_name: 调用方 Agent 名称（可选，用于 Agent 工具权限校验）
        
        Returns:
            执行结果
        """
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
        
        logger.info(f"执行工具调用: {tool_name}, 参数: {arguments}")
        
        # 1. 查找工具定义
        tool_def = self.registry.get_tool(tool_name)
        if not tool_def:
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"未知工具: {tool_name}"
            )
        
        # 2. 安全检查
        allowed, message = self._check_security(tool_name, arguments, agent_name)
        if not allowed:
            # 需要用户确认
            if not await self._request_user_confirmation(message):
                return ToolExecutionResult(
                    success=False,
                    output="",
                    error="用户拒绝了操作"
                )
        
        # 3. 执行 Pre Hooks
        pre_context = ToolExecutionContext(
            tool_name=tool_name,
            arguments=arguments,
            result=None  # Pre Hook 时 result 为 None
        )
        await self.hook_registry.execute_pre_hooks(pre_context)
        
        # 4. 执行工具
        try:
            result = await tool_def.handler(**arguments)
            
            # 5. 收集临时文件并创建 Post Hook 上下文
            temp_files = []
            if isinstance(result, dict) and "file_id" in result:
                # 如果返回结果包含 file_id，记录到上下文中供 Hook 清理
                from my_agent.core.tools.pagination import get_pagination_manager
                pagination_mgr = get_pagination_manager()
                file_path = str(pagination_mgr.get_temp_file_path(result["file_id"]))
                temp_files.append(file_path)
            
            post_context = ToolExecutionContext(
                tool_name=tool_name,
                arguments=arguments,
                result=result if isinstance(result, dict) else {"output": str(result)},
                temp_files_created=temp_files
            )
            
            # 6. 执行 Post Hooks
            await self.hook_registry.execute_post_hooks(post_context)
            
            return ToolExecutionResult(success=True, output=str(result))
        except Exception as e:
            logger.error(f"工具执行失败: {e}")
            return ToolExecutionResult(
                success=False,
                output="",
                error=f"工具执行失败: {str(e)}"
            )
    
    def _check_security(
        self, 
        tool_name: str, 
        arguments: dict, 
        agent_name: str | None = None
    ) -> tuple[bool, str]:
        """执行安全检查。
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            agent_name: 调用方 Agent 名称（可选，用于 Agent 工具权限校验）
            
        Returns:
            (是否允许直接执行, 提示信息)
        """
        # Agent 维度的工具权限校验（物理隔离）
        if agent_name:
            allowed, msg = self.security_checker.check_agent_tool_access(agent_name, tool_name)
            if not allowed:
                return False, msg
        
        if tool_name in [READ_CODE_WINDOW, LOCATE_CODE]:
            return self.security_checker.check_read_access(arguments["file_path"])
        elif tool_name == PATCH_CODE_WINDOW:
            return self.security_checker.check_write_access(arguments["file_path"])
        elif tool_name == CREATE_FILE:
            return self.security_checker.check_create_access(arguments["file_path"])
        
        # 其他工具默认允许
        return True, ""
    
    async def _request_user_confirmation(self, message: str) -> bool:
        """请求用户确认。
        
        Returns:
            用户是否确认
        """
        self.console.print(f"\n[yellow]⚠️ 安全提示:[/yellow]\n{message}")
        return Confirm.ask("是否继续？", default=False)
