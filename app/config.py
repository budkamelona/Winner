from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    BOT_USERNAME: str
    DATABASE_URL: str
    TIMEZONE: str = "Europe/Moscow"
    ADMIN_TELEGRAM_ID: int

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
