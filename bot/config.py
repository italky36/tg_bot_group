from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Bot configuration settings."""

    bot_token: str = Field(..., description="Telegram Bot Token")
    support_group_id: int = Field(..., description="Support Group Chat ID")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./support_bot.db",
        description="Database connection URL"
    )
    admin_secret_key: str = Field(
        default="change_me_in_production",
        description="Secret key for admin panel"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
