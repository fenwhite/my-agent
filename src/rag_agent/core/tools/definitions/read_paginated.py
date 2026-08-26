from rag_agent.core.tools.definitions.base import ToolDefinition
from rag_agent.core.tools.pagination import get_pagination_manager

async def read_paginated_impl(
        file_id: str,
        page: int = 1,
        page_size: int | None = None
) -> dict:
    
    pagination_mgr = get_pagination_manager()

    return pagination_mgr.read_paginated(file_id, page, page_size)

def create_read_paginated_tool() -> ToolDefinition:
    return ToolDefinition(
        name="read_paginated",
        description="分页读取长文本内容。用于查看由 read_file_content 或 execute_sandbox_command 生成的分页结果",
        parameters_schema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "临时文件标识符(由其他工具返回)"
                },
                "page": {
                    "type": "integer",
                    "description": "页码(从1开始)",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "每页行数",
                    "default": 50
                }
            },
            "required": ["file_id"]
        },
        handler=read_paginated_impl,
        requires_confirmation=False,
        risk_level="low"
    )