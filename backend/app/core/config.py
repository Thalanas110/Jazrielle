from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[3] / "ai" / "qwen3-0.6b-q4_k_m.gguf"
DEFAULT_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parents[3] / "ai" / "system-prompt.md"
DEFAULT_ACTION_CONFIG_PATH = Path(__file__).resolve().parents[3] / "ai" / "assistant-actions.json"
DEFAULT_CORS_ORIGINS = ",".join(
    (
        "http://localhost:20380",
        "http://127.0.0.1:20380",
        "tauri://localhost",
        "http://tauri.localhost",
    )
)


class Settings(BaseSettings):
    app_name: str = "Jazrielle API"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    cors_origins: str = DEFAULT_CORS_ORIGINS
    model_path: str = str(DEFAULT_MODEL_PATH)
    system_prompt_path: str = str(DEFAULT_SYSTEM_PROMPT_PATH)
    action_config_path: str = str(DEFAULT_ACTION_CONFIG_PATH)
    model_context_size: int = 4096
    model_max_tokens: int = 512
    tinyfish_api_key: str | None = None
    tinyfish_location: str = "PH"
    tinyfish_language: str = "en"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
