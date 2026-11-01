"""Apply the SQL files in backend/migrations to the database, in order.

    python backend/apply_migrations.py

Every file is written so that running it again changes nothing, so this is safe to run on any database,
including one that is already up to date. A database created by `python backend/seed.py` does not need it.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from backend.app.core.database import Base, engine
import backend.app.models.models  # noqa: F401  (registers the tables)

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


def statements(sql: str):
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    return [part.strip() for part in "\n".join(lines).split(";") if part.strip()]


def main() -> None:
    Base.metadata.create_all(bind=engine)  # new tables first
    files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql"))
    for name in files:
        with open(os.path.join(MIGRATIONS_DIR, name), encoding="utf-8") as handle:
            parts = statements(handle.read())
        with engine.begin() as connection:
            for statement in parts:
                connection.execute(text(statement))
        print(f"applied {name} ({len(parts)} statements)")
    print("Database is up to date.")


if __name__ == "__main__":
    main()
