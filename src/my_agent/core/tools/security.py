"""File access security checker."""

from pathlib import Path
from typing import List, Tuple

from my_agent.core.exceptions import FileTooLargeError, SecurityError
from my_agent.config.settings import get_settings
from my_agent.utils.path_resolver import resolve_smart_path, resolve_creation_path


class FileSecurityChecker:
    """文件访问安全检查器。
    
    职责：
    1. 验证文件路径是否在白名单内
    2. 检测危险操作（如路径遍历攻击）
    3. 检查文件大小限制
    4. 检查文件后缀白名单
    5. 返回检查结果和需要的确认信息
    6. 校验 Sub-Agent 工具访问权限
    """
    
    def __init__(self, whitelist_dirs: List[str]):
        """
        Args:
            whitelist_dirs: 白名单目录列表（相对于项目根目录）
        """
        self.whitelist_dirs = [Path(d).resolve() for d in whitelist_dirs]
        self.settings = get_settings()
    
    
    def check_read_access(self, file_path: str) -> Tuple[bool, str]:
        """检查是否允许读取该文件。
        
        Returns:
            (是否允许, 原因/提示信息)
        """
        try:
            target = resolve_smart_path(file_path)
        except Exception as e:
            return False, f"无效的文件路径: {e}"
        
        # 检查路径遍历攻击
        if ".." in str(file_path):
            return False, "检测到危险的路径遍历操作"
        
        # 检查白名单
        for allowed_dir in self.whitelist_dirs:
            try:
                if target.is_relative_to(allowed_dir):
                    return True, ""
            except ValueError:
                # is_relative_to 在不相关时抛出 ValueError
                continue
        
        # 不在白名单内，需要用户确认
        return False, f"文件不在白名单目录中，需要用户确认\n允许访问: {target}"
    
    def check_write_access(self, file_path: str) -> Tuple[bool, str]:
        """检查是否允许写入该文件（修改已有文件场景）。
        
        Returns:
            (是否允许, 原因/提示信息)
        """
        try:
            target = resolve_smart_path(file_path)
        except Exception as e:
            return False, f"无效的文件路径: {e}"
        
        # 检查路径遍历攻击
        if ".." in str(file_path):
            return False, "检测到危险的路径遍历操作"
        
        # 检查白名单
        in_whitelist = False
        for allowed_dir in self.whitelist_dirs:
            try:
                if target.is_relative_to(allowed_dir):
                    in_whitelist = True
                    break
            except ValueError:
                continue
        
        if not in_whitelist:
            return False, f"文件不在白名单目录中，需要用户确认\n允许访问: {target}"
        
        # 检查文件后缀白名单
        if target.suffix and target.suffix not in self.settings.tool_allowed_extensions:
            raise SecurityError(
                f"不允许写入该类型的文件。允许的后缀: {self.settings.tool_allowed_extensions}"
            )
        
        # 文件必须存在（修改场景）
        if not target.exists():
            return False, f"文件不存在，无法修改\n路径: {target}"
        
        return True, f"文件已存在，将被修改\n路径: {target}\n大小: {target.stat().st_size} bytes"
    
    def check_create_access(self, file_path: str) -> Tuple[bool, str]:
        """检查是否允许创建该文件（创建新文件场景）。
        
        Returns:
            (是否允许, 原因/提示信息)
        """
        try:
            target = resolve_creation_path(file_path)
        except Exception as e:
            return False, f"无效的文件路径: {e}"
        
        # 检查路径遍历攻击
        if ".." in str(file_path):
            return False, "检测到危险的路径遍历操作"
        
        # 检查白名单
        in_whitelist = False
        for allowed_dir in self.whitelist_dirs:
            try:
                if target.is_relative_to(allowed_dir):
                    in_whitelist = True
                    break
            except ValueError:
                continue
        
        if not in_whitelist:
            return False, f"文件不在白名单目录中，需要用户确认\n允许访问: {target}"
        
        # 检查文件后缀白名单
        if target.suffix and target.suffix not in self.settings.tool_allowed_extensions:
            raise SecurityError(
                f"不允许写入该类型的文件。允许的后缀: {self.settings.tool_allowed_extensions}"
            )
        
        # 文件不能已存在（创建场景）
        if target.exists():
            return False, f"文件已存在，无法创建\n路径: {target}"
        
        return True, f"确认创建新文件\n路径: {target}"

    def check_agent_tool_access(self, agent_name: str, tool_name: str) -> Tuple[bool, str]:
        """校验 Sub-Agent 是否有权调用指定工具（物理隔离白名单校验）。
        
        Args:
            agent_name: Agent 名称
            tool_name: 工具名称
            
        Returns:
            (是否允许, 原因/提示信息)
        """
        from my_agent.core.orchestra.registry import AgentRegistry
        
        registry = AgentRegistry.get_instance()
        agent = registry.get_agent(agent_name)
        
        if not agent:
            return False, f"未知 Agent: {agent_name}"
        
        if tool_name not in agent.capability.private_tools:
            return False, f"Agent '{agent_name}' 未授权调用工具 '{tool_name}'"
        
        return True, ""
