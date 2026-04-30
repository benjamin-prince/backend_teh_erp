from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True,
    )

    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # App
    APP_NAME: str = "TEHTEK ERP API"
    APP_VERSION: str = "2.0.0"
    APP_ENV: str = "production"
    DEBUG: bool = False

    # Security
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15

    # CORS
    ALLOWED_ORIGINS: List[str]

    # Super Admin
    SUPERADMIN_EMAIL: str
    SUPERADMIN_PHONE: str
    SUPERADMIN_PASSWORD: str
    SUPERADMIN_FIRST_NAME: str
    SUPERADMIN_LAST_NAME: str


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()