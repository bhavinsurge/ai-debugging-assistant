from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "RootCause"
    api_host: str = "0.0.0.0"
    api_port: int = 8009
    cors_origins: str = "http://localhost:3009"

    jwt_secret: str = "rootcause-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    refresh_token_days: int = 7
    cookie_secure: bool = False

    database_url: str = (
        "postgresql://rootcause:rootcause_dev_password@localhost:5439/rootcause"
    )
    database_url_test: str = (
        "postgresql://rootcause:rootcause_dev_password@localhost:5439/rootcause_test"
    )

    redis_url: str = "redis://localhost:6384/0"

    llm_provider: str = "mock"  # mock | ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    embedding_dim: int = 384
    cache_ttl_seconds: int = 120


@lru_cache
def get_settings() -> Settings:
    return Settings()
