import asyncio
from pathlib import Path

from sqlalchemy import text

from .config import Settings
from .db import create_session_factory


async def apply_migrations() -> None:
    settings = Settings.from_env()
    factory = create_session_factory(settings)
    migration_dir = Path(__file__).resolve().parent.parent / "migrations"
    statements = []
    for migration in sorted(migration_dir.glob("*.sql")):
        statements.extend(
            statement.strip()
            for statement in migration.read_text(encoding="utf-8").split(";")
            if statement.strip()
        )
    async with factory() as db:
        for statement in statements:
            await db.execute(text(statement))
        await db.commit()


if __name__ == "__main__":
    asyncio.run(apply_migrations())
