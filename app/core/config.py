from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartAttend"
    database_url: str = "sqlite:///./smartattend.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()