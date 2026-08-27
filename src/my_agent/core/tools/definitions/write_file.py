from pathlib import Path

from my_agent.core.tools.definitions.base import ToolDefinition
from my_agent.config.settings import get_settings

async def write_file_impl(
        file_path: str,
        content: str,
        encoding: str = "utf-8"
) -> dict:

    target = Path(file_path)

    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(target, 'w', encoding=encoding) as f:
            f.write(content)

            return {
                "success": True,
                "message": f"文件已成功写入: {file_path} ({len(content)}) 字符",
                "file_path": file_path,
                "size": len(content),
            }
    except PermissionError:
        raise PermissionError(f"写入权限: {file_path}")
    except OSError as e:
        raise OSError(f"写入文件失败: {e}")
    


def create_write_file_tool() -> ToolDefinition:
    settings = get_settings
    return ToolDefinition(
        name="write_file",
        description=f"将内容写入文件。如果文件已存在就会被覆盖。允许的后缀: {settings.tool_allowed_extensions}",
        parameters_schema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "目标文件路径"
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容"
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码",
                    "default": "utf-8"
                }
            },
            "required": ["file_path", "content"]
        },
        handler=write_file_impl,
        requires_confirmation=True,
        risk_level="high"
    )