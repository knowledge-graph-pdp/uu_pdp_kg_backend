from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "UU PDP KG Backend"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    GRAPH_PATH: Path = BASE_DIR / "data" / "pdp_graph.ttl"
    MIN_QUERY_COVERAGE: float = 0.8
    MIN_RETRIEVAL_SCORE: float = 2.0
    LLM_API_KEY: SecretStr | None = None
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: float = 12.0
    LLM_JSON_MODE: bool = True
    LLM_MAX_CONTEXT_PROVISIONS: int = 12

    @property
    def llm_enabled(self) -> bool:
        key = self.LLM_API_KEY
        return key is not None and key.get_secret_value().strip() != ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
