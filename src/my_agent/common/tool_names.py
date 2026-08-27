"""Tool name constants.

所有工具名称统一在此处定义，避免字符串散落在各处导致不一致。
"""

# ---------------------------------------------------------------------------
# 文件操作工具
# ---------------------------------------------------------------------------

READ_CODE_WINDOW = "read_code_window"
"""读取文件指定行号区间的代码"""

LOCATE_CODE = "locate_code"
"""基于关键词定位代码行"""

PATCH_CODE_WINDOW = "patch_code_window"
"""修改已有文件的指定行号区间的代码"""

CREATE_FILE = "create_file"
"""创建新文件并写入完整内容"""

# ---------------------------------------------------------------------------
# 目录与搜索工具
# ---------------------------------------------------------------------------

LIST_DIRECTORY = "list_directory"
"""列出指定目录的内容"""

SEARCH_FILE_NAMES = "search_file_names"
"""根据文件名模式搜索文件"""

# ---------------------------------------------------------------------------
# 命令执行工具
# ---------------------------------------------------------------------------

EXECUTE_SANDBOX_COMMAND = "execute_sandbox_command"
"""在沙箱中执行预定义的命令"""

# ---------------------------------------------------------------------------
# 工具名称集合（用于快速判断）
# ---------------------------------------------------------------------------

READ_TOOLS = frozenset([READ_CODE_WINDOW, LOCATE_CODE])
"""读类工具"""

WRITE_TOOLS = frozenset([PATCH_CODE_WINDOW, CREATE_FILE])
"""写类工具"""

ALL_TOOL_NAMES = frozenset([
    READ_CODE_WINDOW,
    LOCATE_CODE,
    PATCH_CODE_WINDOW,
    CREATE_FILE,
    LIST_DIRECTORY,
    SEARCH_FILE_NAMES,
    EXECUTE_SANDBOX_COMMAND,
])
"""所有已注册工具名称"""
