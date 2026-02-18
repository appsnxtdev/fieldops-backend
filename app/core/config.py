from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""
    ENV: str = "development"
    DEBUG: bool = False
    CORE_SERVICE_URL: str = ""
    CORE_SERVICE_API_KEY: str = ""


def get_settings() -> Settings:
    return Settings()
