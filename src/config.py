"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    jwt_secret: str = "change-me-in-production-at-least-256-bits"
    milvus_uri: str = "http://localhost:19530"
    weather_city: str = "London"
    todo_mcp_url: str = "http://localhost:8001/mcp"


settings = Settings()
