from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str

    # JWT (UR-007, UR-008, UR-010)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # App
    APP_ENV: str = "production"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["https://app.tehtek.com", "https://customer.tehtek.com"]

    # Seed
    SUPERADMIN_EMAIL: str = "admin@tehtek.com"
    SUPERADMIN_PHONE: str = ""
    SUPERADMIN_PASSWORD: str
    SUPERADMIN_FIRST_NAME: str = "Benjamin"
    SUPERADMIN_LAST_NAME: str = "Boule Fogang"


settings = Settings()
