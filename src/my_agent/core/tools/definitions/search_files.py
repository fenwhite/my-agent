from pathlib import Path
from typing import Optional

from my_agent.core.tools.definitions.base import ToolDefinition
from my_agent.common.exceptions import ToolError

async def search_file_nams_impl(
        pattern: str,
        max_results: Optional[int] = None,
        search_dir: str = "."
) -> dict:
    if max_results is None:
        max_results = 50

    search_path = Path(search_dir)
    if not search_path.exists():
        raise ToolError(f"搜索目录不存在: {search_dir}")
    
    glob_pattern = pattern if '**' in pattern else f"**/{pattern}"

    try:
        matches = [str(p.relative_to(search_path)) for p in search_path.glob(glob_pattern) if p.exists]

        truncated = len(matches) > max_results
        limited_matches = matches[:max_results]

        results = []
        for match in limited_matches:
            full_path = search_path / match
            results.append({
                "path": str(full_path),
                "name": full_path.name,
                "type": "file" if full_path.is_file() else "directory"
            })
        
        return {
            "pattern": pattern,
            "search_dir": str(search_path),
            "results": results,
            "total_count": len(matches),
            "truncated": truncated
            }
    except Exception as e:
        raise ToolError(f"文件搜索失败: {e}")
    
def create_search_files_tool() -> ToolDefinition:
    return ToolDefinition(
        name="search_file_names",
        description="根据文件名模式搜索文件。支持通配符(* 和 ?)。适用于快速定位文件位置",
        parameters_schema={
            "type": "object",
            "property": {
                "pattern": {
                    "type": "string",
                    "descrption": "文件名模式，支持通配符。(例如：*.py, test_*.py, README.*)"
                },
                "max_results": {
                    "type": "integer",
                    "descrption": "最大返回结果数",
                    "default": 50
                },
                "search_dir": {
                    "type": "string",
                    "descrption": "搜索起始目录",
                    "default": "."
                },
            },
            "reuired": ["pattern"]
        },
        handler=search_file_nams_impl,
        requires_confirmation=False,
        risk_level="low"
    )