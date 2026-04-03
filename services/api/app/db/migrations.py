from __future__ import annotations

from pathlib import Path

from app.db.database import db_connection, get_migrations_dir


def apply_migrations() -> None:
    migrations_dir = get_migrations_dir()
    with db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        applied = {
            row["version"] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }
        for migration in sorted(Path(migrations_dir).glob("*.sql")):
            if migration.name in applied:
                continue
            sql = migration.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations(version) VALUES (?)",
                (migration.name,),
            )

