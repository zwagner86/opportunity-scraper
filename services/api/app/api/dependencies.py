from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from app.db.database import db_connection


def get_db() -> Iterator[sqlite3.Connection]:
    with db_connection() as conn:
        yield conn

