"""Application settings, loaded from environment variables / .env.

pydantic-settings maps each field to an env var of the same name (case-insensitive),
so `GEMINI_API_KEY=...` in .env populates `settings.gemini_api_key`.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://recruit:change-me@localhost:5432/recruitment"

    # AI: "auto" uses Gemini when a key is present, otherwise the offline heuristic provider.
    ai_provider: str = "auto"  # auto | gemini | fake
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"

    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 10

    # Base URL of n8n webhooks, e.g. http://localhost:5678/webhook. Empty = notifications off.
    n8n_webhook_url: str = ""
    # Where the dashboard lives — used to build links in notifications.
    public_app_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
