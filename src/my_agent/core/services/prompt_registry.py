from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from my_agent.utils.logging import get_logger

logger = get_logger(__name__)

class PromptLoader:
    @staticmethod
    def load_all_prompts(prompts_dir: Path) -> dict[str, str]:
        prompts = {}
        if not prompts_dir.exists():
            logger.warning(f"Prompt 目录不存在 {prompts_dir}")
            return prompts
        
        for md_file in prompts_dir.glob("*.md"):
            try:
                name = md_file.stem
                content = md_file.read_text(encoding="utf-8")
                prompts[name] = content
                logger.debug(f"已加载 prompt: {name}")
            except Exception as e:
                logger.error(f"加载 prompt 文件失败 {md_file.name}")
        return prompts
    
class PromptRegistry:
    _instance: Optional["PromptRegistry"] = None
    _lock = threading.Lock()

    def __init__(self):
        if PromptRegistry._instance is not None:
            raise RuntimeError("PromptRegistry 是单例，请使用 get_instance 方法")
        self._prompts: dict[str, str] = {}
        self._current_name: str = ""
        self._fallback_prompts: dict[str, str] = {}
        self._initialized = False
    
    @classmethod
    def get_instance(cls) -> "PromptRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def initialize(self, prompts_dir: Path, default_prompt: str = "rem") -> None:
        if self._initialized:
            logger.warning("PromptRegistry 已经初始化")
            return
        
        self._load_fallback_prompts()

        external_prompts = self._ensure_prompts_dir(prompts_dir)

        if external_prompts:
            self._prompts.update(external_prompts)
            logger.info(f"从 {prompts_dir} 加载了 {len(external_prompts)} 个 prompt")
        else:
            logger.warning(f"Prompt 目录 {prompts_dir} 为空，使用内置 Prompt")

        if default_prompt in self._prompts:
            self._current_name = default_prompt
        elif self._fallback_prompts:
            self._current_name = list(self._fallback_prompts.keys())[0]
            logger.warning(f"默认 prompt '{default_prompt}' 不存在，使用 '{self._current_name}'")
        else:
            raise RuntimeError("没有可用的 prompt")
        
        self._initialized = True
        logger.info(f"PromptRegistry 初始化完成，当前 prompt: {self._current_name}")

    def _load_fallback_prompts(self) -> None:
        fallback_dir = Path(__file__).parent.parent.parent / "config" / "prompts"

        if not fallback_dir.exists():
            logger.error(f"内置 fallback prompt 目录不存在: {fallback_dir}") 
            return
        
        self._fallback_prompts = PromptLoader.load_all_prompts(fallback_dir)

        if self._fallback_prompts:
            logger.info(f"已加载 {len(self._fallback_prompts)} 个内置 prompt")
        else:
            logger.warning("没有找到内置 fallback prompt 文件")

    def _ensure_prompts_dir(self, prompts_dir: Path) -> dict[str, str]:
        if not prompts_dir.exists():
            logger.warning(f"Prompt 目录不存在，自动创建 {prompts_dir}")
            prompts_dir.mkdir(parents=True, exist_ok=True)
            return {}
        return PromptLoader.load_all_prompts(prompts_dir)
    
    def switch(self, name: str) -> None:
        if name not in self._prompts and name not in self._fallback_prompts:
            available = self.list_available()
            raise ValueError(
                f"Prompt '{name}' 不存在，可用 prompt： {','.join(available) if available else '无'}"
            )
        
        with self._lock:
            self._current_name = name
            logger.info(f"已切换到 prompt: {name}")

    def get_current(self) -> str:
        if not self._initialized:
            raise RuntimeError("PromptRegistry 尚未初始化")
        
        if self._current_name in self._prompts:
            return self._prompts[self._current_name]
        elif self._current_name in self._fallback_prompts:
            return self._fallback_prompts[self._current_name]
        else:
            raise RuntimeError(f"当前 Prompt '{self._current_name}' 不存在")
        
    def list_available(self) -> list[str]:
        all_names = set(self._prompts.keys()) | set(self._fallback_prompts.keys())
        return sorted(all_names)
    
    def get(self, name: str) -> str:
        if name in self._prompts:
            return self._prompts[name]
        elif name in self._fallback_prompts:
            return self._fallback_prompts[name]
        else:
            raise ValueError(f"Prompt '{name}' 不存在")

    def get_no_raise(self, name: str) -> str: 
        if name in self._prompts:
            return self._prompts[name]
        return ""
    
        
    @property
    def current_name(self) -> str:
        return self._current_name
    
