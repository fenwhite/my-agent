from pathlib import Path

from rag_agent.core.tools.hooks.core import ToolExecutionContext
from rag_agent.utils.logging import get_logger

logger = get_logger(__name__)

async def cleanup_temp_files_hook(context: ToolExecutionContext):
    if not context.temp_files_created:
        return
    
    logger.info(f"开始清理 {len(context.temp_files_created)} 个临时文件")

    for file_path in context.temp_files_created:
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.debug(f"已删除临时文件: {file_path}")
            else:
                logger.debug(f"临时文件不存在: {file_path}")
        except Exception as e:
            logger.error(f"临时文件删除失败 [{file_path}]: {e}")
    
    logger.info(f"临时文件清理完成")