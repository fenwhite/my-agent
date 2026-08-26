from pathlib import Path
from typing import List, Tuple

from rag_agent.common.exceptions import ToolError, SecurityError
from rag_agent.config.settings import get_settings

class FileSecurityChecker:
    def __init__(self, whitelist_dirs: List[str]):
        self.whitelist_dirs = whitelist_dirs
        self.settings = get_settings()

    def check_read_access(self, file_path: str) -> Tuple[bool, str]:
        try:
            target = Path(file_path).resolve()
        except Exception as e:
            raise ToolError(f"无效的文件路径: {e}")
        
        if not target.exists():
            raise ToolError(
                f"文件不存在: {target}\n\n"
                f"请检查:\n"
                f"1. 文件路径是否正确(支持相对路径、绝对路径和Python模块路径)\n"
                f"2. 是否使用了 locate_code 获取正确的文件路径\n"
                f"3. 文件是否已被删除或移动")

        if ".." in file_path:
            return False, "检测到危险的路径便利操作"
        
        for allow_dir in self.whitelist_dirs:
            try:
                if target.is_relative_to(allow_dir):
                    return True, ""
            except ValueError:
                continue
        return False, f"文件不在白名单目录中, 需要用户确认\n 允许访问: {file_path}"
    
    def check_write_access(self, file_path: str) -> Tuple[bool, str]:
        try:
            target = Path(file_path).resolve()
        except Exception as e:
            raise ToolError(f"无效的文件路径: {e}")
        
        if target.suffix and target.suffix not in self.settings.tool_allowed_extensions:
            return False, (
                f"不允许写入该类型的文件. 允许的后缀: {self.settings.tool_allowed_extensions}"
            )
        
        if target.exists():
            return False, f"⚠ 文件已存在, 将被覆盖\n路径: {file_path}\n"
        
        return False, f"确认写入新文件\n路径: {file_path}"