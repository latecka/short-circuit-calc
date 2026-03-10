"""Application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Short-Circuit Calculator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    BACKEND_PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite:///./short_circuit.db"

    # Authentication
    SECRET_KEY: str = "change-this-to-a-secure-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
