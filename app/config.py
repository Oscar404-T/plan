try:
    # Preferred for pydantic v2
    from pydantic_settings import BaseSettings, SettingsConfigDict
    _BaseSettings = BaseSettings
    _SettingsConfig = SettingsConfigDict
except Exception:
    try:
        # Fallback for older pydantic versions (v1)
        from pydantic import BaseSettings
        _BaseSettings = BaseSettings
        _SettingsConfig = None
    except Exception as exc:  # pragma: no cover - environment issue
        raise RuntimeError(
            "pydantic-settings or pydantic is not installed. Install with: `python3 -m pip install pydantic pydantic-settings`"
        ) from exc


import os
from typing import Optional


class Settings(_BaseSettings):
    # Read from the same env vars as `.env.example` (MYSQL_USER, MYSQL_PASSWORD, ...)
    mysql_user: Optional[str] = None
    mysql_password: Optional[str] = None
    mysql_host: Optional[str] = None
    mysql_port: Optional[int] = None
    mysql_db: Optional[str] = None

    if _SettingsConfig is not None:
        model_config = _SettingsConfig(env_file=".env", env_file_encoding="utf-8")
    else:  # pydantic v1 compatibility
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"

    @property
    def database_url(self) -> str:
        """Return the DB URL. Priority:
        1. `DATABASE_URL` env var
        2. MySQL vars (`MYSQL_USER`, `MYSQL_PASSWORD`, ...)
        3. Fallback to a local SQLite DB for development
        """
        # 1) Prefer explicit DATABASE_URL environment variable
        env_db = os.getenv("DATABASE_URL")
        if env_db:
            return env_db

        # 2) Build from MYSQL_* vars when available
        if self.mysql_user and self.mysql_password:
            return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"

        # 3) Fallback to a local sqlite DB to make local dev effortless
        return "sqlite:///./dev.db"


settings = Settings()
