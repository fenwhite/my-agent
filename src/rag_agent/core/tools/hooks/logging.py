from rag_agent.core.tools.hooks.core import ToolExecutionContext
from rag_agent.utils.logging import get_logger

logger = get_logger(__name__)

async def log_tool_call_hook(context: ToolExecutionContext):
    logger.info(f"即将执行工具: {context.tool_name}")
    logger.debug(f"参数: {context.arguments}")