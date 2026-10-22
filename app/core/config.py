from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartAttend"
    database_url: str = "sqlite:///./smartattend.db"

    # No default on purpose: the app must not start without a real secret.
    secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = 60
    cookie_secure: bool = False  # set COOKIE_SECURE=true when served over HTTPS

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()