from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Pixel Forge API"
    app_env: str = "development"
    public_base_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:3000,https://forge-pixel-forge.onrender.com"
    trusted_hosts: str = "localhost,127.0.0.1,pixel-forge-api.onrender.com"

    max_upload_mb: int = 8
    max_image_pixels: int = 25_000_000
    max_model_mb: int = 100

    output_dir: str = "outputs"
    private_source_dir: str = "private_sources"
    source_url_ttl_seconds: int = 3600
    source_signing_secret: str = "development-only-source-signing-secret-change-me"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.1-flash-lite"

    threews_base_url: str = "https://three.ws"
    threews_default_tier: str = "draft"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [item.strip() for item in self.trusted_hosts.split(",") if item.strip()]

    @property
    def output_path(self) -> Path:
        path = Path(self.output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def source_path(self) -> Path:
        path = Path(self.private_source_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def max_model_bytes(self) -> int:
        return self.max_model_mb * 1024 * 1024

    @model_validator(mode="after")
    def validate_security_settings(self):
        if self.max_upload_mb < 1 or self.max_upload_mb > 25:
            raise ValueError("MAX_UPLOAD_MB must be between 1 and 25.")

        if self.max_image_pixels < 1_000_000 or self.max_image_pixels > 100_000_000:
            raise ValueError("MAX_IMAGE_PIXELS is outside the allowed range.")

        if self.max_model_mb < 1 or self.max_model_mb > 500:
            raise ValueError("MAX_MODEL_MB is outside the allowed range.")

        if not 300 <= self.source_url_ttl_seconds <= 7200:
            raise ValueError("SOURCE_URL_TTL_SECONDS must be between 300 and 7200.")

        if self.is_production:
            if not self.public_base_url.startswith("https://"):
                raise ValueError("PUBLIC_BASE_URL must use HTTPS in production.")

            if not self.threews_base_url.startswith("https://"):
                raise ValueError("THREEWS_BASE_URL must use HTTPS in production.")

            if (
                len(self.source_signing_secret) < 32
                or self.source_signing_secret.startswith("development-only-")
            ):
                raise ValueError(
                    "SOURCE_SIGNING_SECRET must be a strong production secret."
                )

            for origin in self.cors_origin_list:
                if not origin.startswith("https://"):
                    raise ValueError("Production CORS origins must use HTTPS.")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
