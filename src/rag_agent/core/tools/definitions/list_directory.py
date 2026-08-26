from pathlib import Path
from typing import Optional

from rag_agent.core.tools.definitions.base import ToolDefinition
from rag_agent.common.exceptions import ToolError

async def list_directory_impl(
        dir_path: str,
        max_entries: Optional[int] = None
) -> dict:
    if max_entries is None:
        max_entries = 100
    
    target = Path(dir_path)

    if not target.exists():
        raise ToolError(f"目录不存在: {dir_path}")
    
    if not target.is_dir():
        raise ToolError(f"路径不是目录：{dir_path}")
    
    try:
        entries = []
        truncate = False
        for i, entry in enumerate(target.iterdir()):
            if i >= max_entries:
                truncate = True
                break

            entry_info = {
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "path": str(entry),
            }

            entries.append(entry_info)
        
        result = {
            "directory": str(target),
            "entries": entries,
            "total_count": target.lstat().st_size,
            "truncate": truncate,
        }

        return result
    except PermissionError:
        raise ToolError(f"无权限访问目录: {dir_path}")
    
def create_list_directory_tool() -> ToolDefinition:
    return ToolDefinition(
        name="list_directory",
        description="列出指定目录的直接子项(文件和子目录)。适用于探索项目结构。仅返回直接子项，不递归",
        parameters_schema={
            "type": object,
            "property": {
                "dir_path": {
                    "type": "string",
                    "descrption": "要列出的目录路径(相对或绝对路径)"
                },
                "max_results": {
                    "type": "integer",
                    "descrption": "最大返回结果数",
                    "default": 100
                },
            },
            "reuired": ["dir_path"]
        },
        handler=list_directory_impl,
        requires_confirmation=False,
        risk_level="low"
    )