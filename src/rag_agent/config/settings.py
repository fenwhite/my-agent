from functools import lru_cache

from pydantic_settings import BaseSettings, SettingConfigDict

class Settings(BaseSettings):

    model_config = SettingConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "RAG Agent"
    debug: bool = False
    log_level: str = "INFO"
    log_file: str = ""
    log_file_max_bytes: int = 10 * 1024 * 1024
    log_file_backup_count: int = 5

    api_key: str = ""
    base_url: str = ""
    default_model: str = ""
    qps_limit: int = 20
    timeout: float = 60.0

    tts_enable: bool = False
    tts_voice: str = "zh-CN-XiaoXiaoNeural"
    tts_timeout: float = 10.0
    tts_max_length: int = 800

    chat_max_turns: int = 20
    chat_context_window: int = 10

    tool_file_whitelist: list[str] = [
        "./"
    ]

    # Toolbox Configuration
    tool_temp_file_ttl_hours: int = 24
    tool_inline_max_lines: int = 100
    tool_page_size: int = 50
    tool_temp_file_ttl_hours: int = 24
    tool_allowed_extensions: list[str] = [
        ".py", ".json", ".md", ".txt"
    ]

@lru_cache
def get_settings() -> Settings:
    return Settings()