from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Pixel Forge API"
    app_env: str = "development"
    public_base_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:3000,https://forge-pixel-forge.onrender.com"
    max_upload_mb: int = 8
    output_dir: str = "outputs"

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
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def output_path(self) -> Path:
        path = Path(self.output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
