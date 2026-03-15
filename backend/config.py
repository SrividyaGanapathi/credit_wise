import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    app_host: str
    app_port: int


settings = Settings(
    database_url=os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/cardwise",
    ),
    app_host=os.getenv("APP_HOST", "0.0.0.0"),
    app_port=int(os.getenv("PORT", os.getenv("APP_PORT", "8000"))),
)
