"""
Application configuration loaded from environment variables via pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration – values are read from .env / environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ──────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://rl_user:rl_password@db:5432/rl_simulator"
    )

    # ── JWT ───────────────────────────────────────────────
    SECRET_KEY: str = "change-me-to-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── RL Engine Defaults ────────────────────────────────
    RL_MAX_STEPS: int = 50
    RL_NUM_AGENTS: int = 3
    RL_NUM_TICKETS: int = 5


settings = Settings()
