import tempfile
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Optional

from my_agent.common.exceptions import ToolError
from my_agent.config.settings import get_settings
from my_agent.utils.logging import get_logger

class PaginationManager:
    def __init__(self):
        self.settings = get_settings()
        self.temp_dir = Path(tempfile.gettempdir()) / "my_agent_temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._source_files = {} # file_id -> source_path
        self._line_count_cache = self._create_line_count_cache()

    def _create_line_count_cache(self):
        @lru_cache
        def cached_count_lines(file_path_str: str, file_mtime: float) -> int:
            return self.count_lines_binary(Path(file_path_str))

    def generate_file_id(self) -> str:
        return uuid.uuid4.hex[:12]
    
    def register_source_file(self, source_path: str) -> str:
        file_id = self.generate_file_id()
        self._source_files[file_id] = source_path
        return file_id
    
    def get_temp_file_path(self, file_id: str) -> Path:
        return self.temp_dir / f"{file_id}.tmp"
    
    def save_to_temp_file(self, content: str) -> str:
        file_id = self.generate_file_id()
        file_path = self.get_temp_file_path(file_id)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return file_id

    def count_lines_binary(self, file_path: Path) -> int:
        count = 0
        with open(file_path, 'rb') as f:
            while True:
                buf = f.read(1024 * 1024)
                if not buf:
                    break
                count += buf.count(b'\n')
        return count
    
    def _get_cache_line_count(self, file_path: Path) -> int:
        try:
            file_mtime = file_path.stat().st_mtime
        except OSError:
            return self.count_lines_binary(file_path)
        
        return self._line_count_cache(str(file_path), file_mtime)

    def read_file_range(
            self,
            file_id: str,
            start_line: int = 1,
            end_line: Optional[int] = None
    ) -> dict:
        source_path = self._source_files.get(file_id)
        if source_path:
            file_path = Path(source_path)
        else:
            file_path = self.get_temp_file_path(file_id)
        
        if not file_path.exists():
            raise ToolError(f"文件不存在： {file_id}")
        
        if start_line < 1:
            raise ToolError(f"起始行号无效: {start_line}。必须 >= 1")
        
        total_lines = self._get_cache_line_count(file_id, file_path)

        if end_line is None:
            end_line = total_lines
        elif end_line > total_lines:
            end_line = total_lines

        if start_line > end_line:
            raise ToolError(
                f"行号范围无效: start_line={start_line}, end_line={end_line}"
            )
        
        lines = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for _ in range(start_line - 1):
                if not f.readline():
                    break
            for _ in range(start_line, end_line + 1):
                line = f.readline()
                if not line:
                    break
                lines.append(line)

        content = ''.join(lines)

        return {
            "content": content,
            "start_line": start_line,
            "end_line": end_line,
            "total_lines": total_lines,
            "lines_read": len(lines),
        }

    def read_paginated(
            self,
            file_id: str,
            page: int = 1,
            page_size: Optional[int] = None
    ) -> dict:
        if page_size is None:
            page_size = self.settings.tool_page_size
        
        file_path = self.get_temp_file_path(file_id)

        if not file_path.exists():
            raise ToolError(f"临时文件不存在: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_lines = len(lines)
        total_pages = (total_lines + page_size - 1) // page_size

        if page < 1 or page > total_pages:
            raise ToolError(
                f"页码无效: {page}. 有效范围: 1-{total_lines}"
            )

        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_lines)

        page_lines = lines[start_idx:end_idx]
        content = ''.join(page_lines)

        return {
            "content": content,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_lines": total_lines,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    
    def should_use_pagination(self, content: str, max_lines: Optional[int] = None) -> bool:
        if max_lines is None:
            max_lines = self.settings.tool_inline_max_lines

        lines = content.split('\n')
        return len(lines) > max_lines
    
    def cleanup_expired_files(self):
        import time

        ttl_seconds = self.settings.tool_temp_file_ttl_hours * 3600
        current_time = time.time()

        cleaned_count = 0
        for file_path in self.temp_dir.glob("*.tmp"):
            file_mtime = file_path.stat().st_mtime
            if current_time - file_mtime > ttl_seconds:
                try:
                    file_path.unlink()
                    cleaned_count += 1
                except Exception as e:
                    pass
            
        if cleaned_count > 0:
            logger = get_logger(__name__)
            logger.info(f"已清理 {cleaned_count} 个过期临时文件")

_pagination_manager = None

def get_pagination_manager() -> PaginationManager:
    global _pagination_manager
    if _pagination_manager is None:
        _pagination_manager = PaginationManager()
    return _pagination_manager
