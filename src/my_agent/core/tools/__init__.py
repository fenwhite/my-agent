from my_agent.core.tools.tool_registry import ToolRegistry
from my_agent.core.tools.executor import ToolExecutor

from my_agent.core.tools.hooks import (
    cleanup_temp_files_hook,
    log_tool_call_hook,
    HookRegistry
)

def initialize_tools():
    registry = ToolRegistry.get_instance()

    from my_agent.core.tools.definitions.write_file import create_write_file_tool
    from my_agent.core.tools.definitions.read_paginated import create_read_paginated_tool

    from my_agent.core.tools.definitions.read_code_window import create_read_code_window_tool
    from my_agent.core.tools.definitions.patch_code_window import create_patch_code_window_tool
    from my_agent.core.tools.definitions.locate_code import create_locate_code_tool
    from my_agent.core.tools.definitions.search_files import create_search_files_tool
    from my_agent.core.tools.definitions.list_directory import create_list_directory_tool
    
    registry.registry(create_write_file_tool())
    registry.registry(create_read_paginated_tool())

    registry.registry(create_read_code_window_tool())
    registry.registry(create_patch_code_window_tool())
    registry.registry(create_locate_code_tool())
    registry.registry(create_search_files_tool())
    registry.registry(create_list_directory_tool())

    hook_registry = HookRegistry.get_instance()
    hook_registry.register_pre_hook(log_tool_call_hook)

    hook_registry.register_post_hook(
        cleanup_temp_files_hook,
        tool_names=["create_patch_code_window_tool"]
    )

__all__ = ["ToolRegistry", "ToolExecutor", "initialize_tools"]