import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    app_host: str
    app_port: int
    auto_init_db: bool


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


settings = Settings(
    database_url=os.getenv("DATABASE_URL", "sqlite:///./cardwise.db"),
    app_host=os.getenv("APP_HOST", "0.0.0.0"),
    app_port=int(os.getenv("PORT", os.getenv("APP_PORT", "8000"))),
    auto_init_db=_get_bool("APP_AUTO_INIT_DB", True),
)
