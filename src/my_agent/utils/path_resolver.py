from pathlib import Path
from glob import glob

from my_agent.common.exceptions import AmbiguousPathError


def resolve_smart_path(file_path: str) -> Path:
    target = Path(file_path)

    if target.is_absolute():
        if not target.exists():
            raise FileNotFoundError(f"文件不存在 {file_path}")
        return target.resolve()
    
    if '.' in file_path and not file_path.endswith(('.py', '.txt', '.md', '.json')):
        module_path =file_path.replace('.', '/') + '.py'
        candidate = Path('src') / module_path
        if candidate.exists():
            return candidate.resolve()
        
    project_root = Path.cwd()
    relative_path = project_root / file_path
    if relative_path.exists():
        return relative_path.resolve()
    
    project_relative = project_root / file_path
    if project_relative.exists():
        return project_relative.resolve()
    
    matches = list(glob(f"**/{file_path}", recursive=True))
    if len(matches) == 1:
        return Path(matches[0]).resolve()
    elif len(matches) > 1:
        candidates = [str(Path(m).resolve()) for m in matches[:5]]
        raise AmbiguousPathError(file_path, candidates)
    
    raise FileNotFoundError(f"文件不存在: {file_path}")


def resolve_creation_path(file_path: str) -> Path:
    """解析文件创建路径，用于创建新文件的场景。
    
    与 resolve_smart_path 不同，此函数不要求文件必须存在。
    
    优先级：
    1. 绝对路径
    2. 相对路径（相对于当前工作目录）
    
    Args:
        file_path: 用户输入的路径字符串
        
    Returns:
        解析后的绝对路径
    """
    target = Path(file_path)
    
    # 1. 绝对路径
    if target.is_absolute():
        return target.resolve()
    
    # 2. 相对路径（相对于当前工作目录）
    relative_path = Path.cwd() / file_path
    return relative_path.resolve()
