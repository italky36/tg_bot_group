from pydantic_settings import BaseSettings
from pydantic import Field


class AdminSettings(BaseSettings):
    """Admin panel configuration."""

    database_url: str = Field(
        default="sqlite+aiosqlite:///./support_bot.db",
        description="Database connection URL"
    )
    admin_secret_key: str = Field(
        default="change_me_in_production",
        description="Secret key for sessions"
    )
    admin_username: str = Field(
        default="admin",
        description="Admin username"
    )
    admin_password: str = Field(
        default="admin",
        description="Admin password"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


admin_settings = AdminSettings()
