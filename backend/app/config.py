import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str
    secret_key: str
    database_url: str
    redis_url: str
    session_cookie_secure: bool
    frontend_origin: str

    @classmethod
    def from_env(cls) -> "Settings":
        secret = os.getenv("SECRET_KEY", "")
        if len(secret) < 32 and os.getenv("APP_ENV", "development") != "test":
            raise RuntimeError("SECRET_KEY must contain at least 32 characters")
        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            secret_key=secret or "test-secret-key-for-tests-only-32-chars",
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://leadpitch:leadpitch@localhost:5432/leadpitch",
            ),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            session_cookie_secure=os.getenv("SESSION_COOKIE_SECURE", "false").lower()
            == "true",
            frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:3000"),
        )
