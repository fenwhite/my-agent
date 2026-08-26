from typing import List, Dict

from rag_agent.core.tools.definitions.base import ToolDefinition
from rag_agent.utils.path_resolver import resolve_smart_path

async def locate_code_impl(
        file_path: str,
        keyword: str,
        case_sensitive: bool = False,
        max_result: int = 20
) -> dict:
    
    target = resolve_smart_path(file_path)

    matches: List[Dict] = []
    truncate: bool = False
    with open(target, 'r', encoding='utf-8') as f:
        search_keyword = keyword if case_sensitive else keyword.lower()
        for line_num, line in enumerate(f, start=1):
            search_line = line if case_sensitive else line.lower()

            if search_keyword in search_line:
                if len(matches) >= max_result:
                    truncate = True
                    break
                else:
                    matches.append({
                        "line_number": line_num,
                        "content": line .rstrip('\n')
                    })
                
    
    result = {
        "file_path": file_path,
        "keyword": keyword,
        "case_sensitive": case_sensitive,
        "matched": matches,
    }

    if not matches:
        result["suggestion"] = (
            f"未找到包含 '{keyword}' 的代码行。请尝试:\n"
            f"1. 检查关键词拼写是否错误\n"
            f"2. 确认文件路径是否正确\n"
        )

    if truncate:
        result["warning"] = (
            f"搜索结果已截断 (最多显示 {max_result} 条)\n"
            f"请使用更精确的关键词或结合上下文进一步筛选"
        )

    return result

def create_locate_code_tool() -> ToolDefinition:
    return ToolDefinition(
        name="locate_code",
        description="当你需要寻找某个函数、变量、报错位置或特定逻辑，但是不知道具体行号时，必须首先调用此工具。它会快速扫描文件并返回包含关键词的行号。此工具极其轻量，不会消耗你的上下文token。请勿尝试盲猜行号",
        parameters_schema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径(支持绝对路径、相对路径和Python模块路径)"
                },
                "keyword": {
                    "type": "string",
                    "description": "需要搜索的青雀关键词或代码片段(例如：'def save_user' 或 'timeout=')。保持简单以获得最佳匹配。"
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "是否区分大小写",
                    "default": False,
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果",
                    "default": 20
                }
            },
            "required": ["file_path", "keyword"]
        },
        handler=locate_code_impl,
        requires_confirmation=False,
        risk_level="low"
    )
