import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    app_host: str
    app_port: int
    firebase_project_id: str | None
    cors_allowed_origins: tuple[str, ...]


settings = Settings(
    database_url=os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/cardwise",
    ),
    app_host=os.getenv("APP_HOST", "0.0.0.0"),
    app_port=int(os.getenv("PORT", os.getenv("APP_PORT", "8000"))),
    firebase_project_id=os.getenv("FIREBASE_PROJECT_ID"),
    cors_allowed_origins=tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            ",".join(
                [
                    "http://localhost:5173",
                    "https://card-wise-app.web.app",
                    "https://card-wise-app.firebaseapp.com",
                ]
            ),
        ).split(",")
        if origin.strip()
    ),
)
