import tempfile
import uuid
from pathlib import Path
from typing import List

from my_agent.core.tools.definitions.base import ToolDefinition
from my_agent.common.exceptions import ToolError
from my_agent.utils.path_resolver import resolve_smart_path

async def patch_code_window_impl(
    file_path: str,
    start_line: int,
    end_line: int,
    expected_old_code: str,
    new_code: str,
    encoding: str = "utf-8"
) -> dict:
    
    target = resolve_smart_path(file_path)
    
    if not target.exists():
        raise ToolError(
            f"文件不存在: {target}\n\n"
            f"请检查:\n"
            f"1. 文件路径是否正确(支持相对路径、绝对路径和Python模块路径)\n"
            f"2. 是否使用了 locate_code 获取正确的文件路径\n"
            f"3. 文件是否已被删除或移动")
    
    if start_line < 1:
        raise ToolError(f"起始行号无效: {start_line}. 必须 >= 1")
    
    if end_line < start_line:
        raise ToolError(f"结束行号不能小于起始行号: end_line={end_line} < start_line={start_line}")
    
    actual_lines: List[str] = []
    with open(target, 'r', encoding=encoding) as f:
        for i, line in enumerate(f, start=1):
            if i > end_line:
                break
            if i > start_line:
                actual_lines.append(line)

    actual_code = ''.join(actual_lines)

    if actual_code != expected_old_code:
        expected_lines = expected_old_code.split('\n')
        actual_lines_list = actual_code.split('\n')

        diff_hit = ""
        for i, (exp, act) in enumerate(zip(expected_lines, actual_lines_list)):
            if exp != act:
                line_num = start_line + i
                diff_hit = f"第 {line_num} 行不同： 期望 '{exp}', 实际 '{act}'"
                break
        if not diff_hit and len(expected_lines) != len(actual_lines_list):
            diff_hit = f"行数不匹配： 期望 {len(expected_lines)} 行， 实际 {len(actual_lines_list)} 行"

        error_message = (
            f"Verification Failed! 你提供的old_code_snippet 与磁盘上的实际代码不匹配。\n\n"
            f"[实际代码]： \n {actual_code} \n\n"
            f"{diff_hit} \n\n"
            f"请重新调用 read_code_window 确认该区间的最新代码和精确缩进，然后重新提交修改" 
        )

        return {
            "success": False,
            "error": error_message,
            "expected": expected_old_code,
            "actual": actual_code,
            "diff_hint": diff_hit,
        }
    
    temp_dir = Path(tempfile.gettempdir() / "rag_agent_patch")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / f"patch_{uuid.uuid4().hex[:8]}.tmp"

    try:
        with open(target, 'r', encoding=encoding) as src, \
             open(temp_file, 'w', encoding=encoding) as dst:
            for i, line in enumerate(src, start=1):
                if i>=start_line:
                    break
                dst.write(line)
            
            dst.write(new_code)
            if not new_code.endswith('\n'):
                dst.write('\n')
            
            for i in range(start_line, end_line + 1):
                src.readline()
                
            for line in src:
                dst.write(line)
        
        target.replace(temp_file)

        modified_lines = end_line - start_line + 1

        return {
            "success": True,
            "message": f"成功修改第 {start_line} - {end_line} 行 (共 {modified_lines} 行)",
            "file_path": str(target)
        }
    except Exception as e:
        if temp_file.exists():
            temp_file.unlink()
        raise ToolError(
            f"修改失败： {e}"
        )
    
def create_patch_code_window_tool() -> ToolDefinition:
    return ToolDefinition(
        name="patch_code_window",
        description="用于修改指定行号区间的代码。此工具包含严格的安全检验：你必须提供该区间在磁盘上的 old_code_snippet (必须与你用 read_code_window 读到的内容逐字、逐空格缩进完全一致)。如果检验失败，修改将被拒绝。",
        parameters_schema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径"
                },
                "start_line": {
                    "type": "integer",
                    "description": "修改起始行号"
                },
                "end_line": {
                    "type": "integer",
                    "description": "修改结束行号(包含)"
                },
                "expected_old_code": {
                    "type": "string",
                    "description": "你即将替换的旧代码片段。必须精确包含缩进和换行符。直接从 read_code_window 的返回结果中复制，不要有任何脑补或修改。"
                },
                "new_code": {
                    "type": "string",
                    "description": "新代码片段"
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码",
                    "default": "utf-8"
                }
            },
            "reuired": ["file_path", "start_line", "end_line", "expected_old_code", "new_code"]
        },
        handler=patch_code_window_impl,
        requires_confirmation=True,
        risk_level="high"
    )