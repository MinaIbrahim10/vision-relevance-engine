from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./vision_relevance.db"

    demo_api_key: str = "demo-local-key"

    vision_provider: str = "mock"
    embedding_provider: str = "mock"

    ollama_base_url: str = "http://localhost:11434"
    ollama_vision_model: str = "llava:latest"
    embedding_model: str = "bge-m3:latest"

    min_vision_confidence: float = 0.60
    min_similarity_score: float = 0.45
    duplicate_threshold: float = 0.94

    ai_budget_usd: float = 1.00

    max_job_attempts: int = 3
    worker_poll_seconds: float = 2.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
