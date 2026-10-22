from functools import lru_cache
from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: str = "development"
    database_url: str = "sqlite:///./noka.db"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1-mini"
    # Route resume extraction and Guide independently; the legacy model serves Scout.
    openai_extraction_model: str = Field(default="gpt-4.1-mini", min_length=1)
    openai_guide_model: str = Field(default="gpt-6-sol", min_length=1)
    tavily_api_key: SecretStr | None = None
    ingestion_secret: SecretStr | None = None
    public_origin: str | None = None
    agent_max_tools: int = Field(default=5, ge=1, le=10)
    agent_max_turns: int = Field(default=4, ge=1, le=8)
    agent_timeout_seconds: int = Field(default=60, ge=5, le=120)
    agent_max_output_tokens: int = Field(default=1200, ge=256, le=3000)
    agent_daily_quota: int = Field(default=20, ge=1, le=100)
    agent_max_concurrent: int = Field(default=2, ge=1, le=4)
    agent_global_concurrent: int = Field(default=8, ge=1, le=16)


@lru_cache
def get_settings() -> Settings:
    return Settings()
