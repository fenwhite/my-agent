from typing import List, Dict

from rag_agent.core.tools.definitions.base import ToolDefinition
from rag_agent.common.exceptions import ToolError
from rag_agent.core.tools.pagination import get_pagination_manager
from rag_agent.utils.path_resolver import resolve_smart_path

async def read_code_window_impl(
        file_path: str,
        start_line: int,
        end_line: int,
        encoding: str = "utf-8",
) -> dict:
    
    target = resolve_smart_path(file_path)
    
    if start_line < 1:
        raise ToolError(f"起始行号无效: {start_line}. 必须 >= 1")
    
    if end_line < start_line:
        raise ToolError(f"结束行号不能小于起始行号: end_line={end_line} < start_line={start_line}")
    
    window_size = end_line - start_line + 1
    max_window_size = 50
    if window_size > max_window_size:
        raise ToolError(
            f"单次读取窗口限制为 {max_window_size} 行。你请求了 {window_size} 行 (第 {start_line} - {end_line} 行)。"
            f"请将区间缩小(例如：使用 locate_code 先定位目标行，然后仅读取目标行前后各20行左右的内容) 并重试"
        )
    
    pagination_mgr = get_pagination_manager()
    total_lines = pagination_mgr.count_lines_binary(target)

    if start_line > total_lines:
        raise ToolError(
            f"起始行号 {start_line} 超出文件范围 (文件共 {total_lines} 行)\n"
            f"请使用 locate_code 重新定位，或调整行号范围"
        )
    
    if end_line > total_lines:
        end_line = total_lines

    lines: List[str] = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for _ in range(start_line - 1):
                if not f.readline():
                    break
            for line_num in range(start_line, end_line + 1):
                line = f.readline()
                if not line:
                    break
                lines.append(line.rstrip('\n'))
    except UnicodeDecodeError as e:
        raise ToolError(
            f"文件编码错误：无法使用 '{encoding}' 编码读取文件 {target}\n"
            f"错误详情： {str(e)}\n\n"
            f"建议：\n"
            f"1. 尝试使用其他编码 (如 'gbk', 'latin-1')\n"
            f"2. 在调用时显示指定 encoding 参数\n"
        )
    except IOError as e:
        raise ToolError(
            f"文件读取失败： {str(e)}\n\n"
            f"请检查：\n"
            f"1. 文件是否被其他程序锁定\n"
            f"2. 是否由足够的读取权限\n"
        )
    except Exception as e:
        raise ToolError(
            f"读取文件时发生未知错误: {type(e).__name__}: {str(e)}\n"
            f"文件路径： {target}\n"
            f"行号范围： {start_line} - {end_line}"
        )


    content = '\n'.join(lines)

    return {
        "file_path": file_path,
        "content": content,
        "start_line": start_line,
        "end_line": end_line,
        "total_lines": total_lines,
        "lines_read": len(lines),
    }

def create_read_code_window_tool() -> ToolDefinition:
    return ToolDefinition(
        name="read_code_window",
        description="在已知行号(通过 locate_code 获得) 的情况下，读取该行周围的一个狭窄窗口。单次读取的最大跨度不超过 50 行 (例如：靶心上下各读 20 行)。",
        parameters_schema={
            "type": object,
            "property": {
                "file_path": {
                    "type": "string",
                    "descrption": "文件路径(支持绝对路径、相对路径和Python模块路径)"
                },
                "start_line": {
                    "type": "integer",
                    "description": "起始行号(必须是正整数)。请基于定位结果合理推算。"
                },
                "end_line": {
                    "type": "integer",
                    "description": "结束行号。必须满足 end_line - start_line <= 50"
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码",
                    "default": "utf-8"
                },
            },
            "reuired": ["file_path", "start_line", "end_line"]
        },
        handler=read_code_window_impl,
        requires_confirmation=False,
        risk_level="low"
    )