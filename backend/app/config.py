from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or backend/.env."""

    app_name: str = "ResumeFit AI API"
    app_version: str = "0.1.0"
    environment: str = "development"
    frontend_url: str = Field(default="http://127.0.0.1:5173")

    mistral_api_key: str | None = None
    mistral_model: str = "mistral-small-latest"
    mongodb_uri: str | None = None
    mongodb_database: str = "resume_fit_ai"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str | None = None
    aws_s3_bucket: str | None = None
    firebase_project_id: str | None = None
    firebase_credentials_path: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_url.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
