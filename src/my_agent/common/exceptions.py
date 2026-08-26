class ToolError(Exception):
    pass

class SecurityError(ToolError):
    pass

class FileTooLargeError(ToolError):
    def __init__(self, file_size: int, max_size: int):
        self.file_size = file_size
        self.max_size = max_size
        super().__init__(f"文件大小 {file_size} 字节超过限制 {max_size} 字节")

class AmbiguousPathError(ToolError):
    def __init__(self, path: str, candidates: list[str]):
        self.path = path
        self.candidates = candidates
        super().__init__(f"找到多个匹配文件: {candidates[:5]}, 请指定完整路径")

class CommandNotFoundError(ToolError):
    pass

class ParameterValidationError(ToolError):
    pass