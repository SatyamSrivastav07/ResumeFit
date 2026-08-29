import base64
import json
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application configuration loaded from environment variables."""

    app_name: str = "ResumeFit AI API"
    app_version: str = "1.0.0"
    app_env: Literal["development", "test", "production"] = "development"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    frontend_url: str = "http://127.0.0.1:5173,http://localhost:5173"
    enable_api_docs: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    mistral_api_key: str | None = None
    mistral_model: str = "mistral-small-latest"
    mistral_timeout_seconds: int = Field(default=45, ge=5, le=120)
    mongodb_uri: str | None = None
    mongodb_database: str = "resume_fit_ai"
    mongodb_server_selection_timeout_ms: int = Field(default=5_000, ge=500, le=30_000)
    mongodb_connect_timeout_ms: int = Field(default=5_000, ge=500, le=30_000)
    mongodb_socket_timeout_ms: int = Field(default=10_000, ge=1_000, le=60_000)
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str | None = None
    aws_s3_bucket: str | None = None
    aws_connect_timeout_seconds: int = Field(default=5, ge=1, le=30)
    aws_read_timeout_seconds: int = Field(default=20, ge=1, le=60)
    firebase_project_id: str | None = None
    firebase_credentials_path: str | None = None
    firebase_credentials_base64: str | None = None

    max_upload_size_mb: int = Field(default=5, ge=1, le=20)
    max_json_body_bytes: int = Field(default=1_000_000, ge=100_000, le=5_000_000)
    presigned_url_expiry_seconds: int = Field(default=900, ge=60, le=3_600)
    rate_limit_authenticated: int = Field(default=120, ge=1, le=10_000)
    rate_limit_ai: int = Field(default=10, ge=1, le=1_000)
    rate_limit_upload: int = Field(default=5, ge=1, le=1_000)
    rate_limit_pdf: int = Field(default=10, ge=1, le=1_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3_600)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    @model_validator(mode="after")
    def validate_environment(self) -> "Settings":
        origins = self.allowed_origins
        if not origins:
            raise ValueError("FRONTEND_URL must contain at least one origin.")
        for origin in origins:
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
                raise ValueError("FRONTEND_URL must contain valid origins without paths.")
        if bool(self.aws_access_key_id) != bool(self.aws_secret_access_key):
            raise ValueError(
                "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be configured together."
            )
        if self.app_env == "production":
            missing = [name for name, value in {
                "MONGODB_URI": self.mongodb_uri,
                "MISTRAL_API_KEY": self.mistral_api_key,
                "AWS_REGION": self.aws_region,
                "AWS_S3_BUCKET": self.aws_s3_bucket,
                "FIREBASE_ADMIN_CREDENTIALS": (
                    self.firebase_credentials_path or self.firebase_credentials_base64
                ),
            }.items() if not value]
            if missing:
                raise ValueError(f"Missing production configuration: {', '.join(missing)}")
            if any(urlparse(origin).scheme != "https" for origin in origins):
                raise ValueError("Production FRONTEND_URL origins must use HTTPS.")
            if (
                self.firebase_credentials_path
                and not self.firebase_credentials_base64
                and not Path(str(self.firebase_credentials_path)).expanduser().is_file()
            ):
                raise ValueError("FIREBASE_CREDENTIALS_PATH does not reference a file.")
            if self.firebase_credentials_base64:
                self.firebase_credentials_from_base64()
        return self

    def firebase_credentials_from_base64(self) -> dict[str, object]:
        """Decode Firebase Admin JSON supplied through a secret environment value."""

        try:
            raw = base64.b64decode(self.firebase_credentials_base64 or "", validate=True)
            value = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("FIREBASE_CREDENTIALS_BASE64 is not valid Base64-encoded JSON.") from exc
        if not isinstance(value, dict):
            raise ValueError("FIREBASE_CREDENTIALS_BASE64 must decode to a JSON object.")
        return value

    @property
    def environment(self) -> str:
        return self.app_env

    @property
    def allowed_origins(self) -> list[str]:
        return list(dict.fromkeys(origin.strip().rstrip("/") for origin in self.frontend_url.split(",") if origin.strip()))

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
