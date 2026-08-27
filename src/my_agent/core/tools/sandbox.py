import re
from typing import List, Tuple

from my_agent.common.exceptions import CommandNotFoundError, ParameterValidationError

COMMAND_WHITELIST = {
    "pytest": ["pytest"],
    "ruff_check": ["ruff", "check"],
    "ruff_fix": ["ruff", "check", "--fix"],
    "ruff_format": ["ruff", "format"],
    "mypy_src": ["mypy", "src"],
    "mypy_all": ["mypy", "src", "tests"],
    "cli_help": ["rag-agent", "--help"],
}

def validate_command(command_key: str) -> Tuple[bool, List[str]]:
    if command_key not in COMMAND_WHITELIST:
        raise CommandNotFoundError(
            f"命令 '{command_key}' 不在白名单中。可用命令: {list(COMMAND_WHITELIST.KEY())}"
        )
    
    return True, COMMAND_WHITELIST[command_key]

def validate_parameters(params: List[str]) -> bool:
    dangerous_patterns = [
        r'[;&|><$`]',
        r'\.\./',
        r'\.\.\\',
        r'^[A-Z]:\\',
        r'^/',
    ]

    for param in params:
        for pattern in dangerous_patterns:
            if re.search(pattern, param):
                raise ParameterValidationError(
                    f"参数包含非法字符，已拒绝执行: '{param}'"
                )
            
    return True

def build_command(command_key: str, extra_params: list[str] | None = None) -> List[str]:
    _, base_command = validate_command(command_key)

    if extra_params:
        validate_parameters(extra_params)
        return base_command + extra_params
    
    return base_command