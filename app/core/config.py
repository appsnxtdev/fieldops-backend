from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file so it works regardless of CWD
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""
    ENV: str = "development"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "https://api.appnxt.cloud,https://saas.appnxt.cloud,https://fieldops.appnxt.cloud"
    LOG_LEVEL: str = "INFO"
    CORE_SERVICE_URL: str = ""
    CORE_SERVICE_API_KEY: str = ""
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""

    # Firebase Configuration
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_CREDENTIALS_PATH: str = ""


@lru_cache()
def get_settings() -> Settings:
    return Settings()
