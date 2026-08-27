from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "My Agent"
    debug: bool = False
    log_level: str = "INFO"
    log_file: str = ""  # Empty means console only; set path to enable file logging
    log_file_max_bytes: int = 10 * 1024 * 1024  # 10MB per file
    log_file_backup_count: int = 5  # Keep 5 rotated files

    # IdeaLab LLM Configuration
    idealab_api_key: str = ""
    idealab_base_url: str = ""
    idealab_default_model: str = ""
    idealab_qps_limit: int = 20
    idealab_timeout: float = 60.0

    # Vector Store
    vector_store_path: str = "./data/vector_store"

    # Retrieval
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5

    # TTS Configuration
    tts_enabled: bool = False
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
    tts_timeout: float = 10.0

    # Chat Configuration
    chat_max_turns: int = 20

    # Prompt Configuration
    prompt_dir: str = "./prompts"
    default_prompt: str = "rem"

    # Tool System Configuration
    tool_file_whitelist: list[str] = [
        "./",
    ]
    enable_tools: bool = True
    
    # Orchestra Configuration
    orchestra_log_dir: str = "./logs/orchestra"
    orchestra_max_retries: int = 3

    # Toolbox Configuration
    tool_inline_max_lines: int = 100     # 内联返回最大行数
    tool_allowed_extensions: list[str] = [
        ".py", ".json", ".toml", ".yaml", ".yml", ".md", ".txt"
    ]


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
