"""Слой хранения: SQLite (leads и feedback).

База создаётся автоматически при первом запуске в data/bot.sqlite3.
Схема идемпотентно создаётся при каждом подключении.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

BASE_DIR = Path(__file__).resolve().parent

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id     TEXT NOT NULL,
    source         TEXT NOT NULL,
    service        TEXT,
    contact        TEXT,
    problem_text   TEXT,
    agent_summary  TEXT,
    missing_info   TEXT,
    status         TEXT NOT NULL DEFAULT 'new',
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL,
    message_text TEXT NOT NULL,
    created_at   TEXT NOT NULL
);
"""


def _db_path() -> Path:
    configured = os.getenv("DB_PATH", "")
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            path = BASE_DIR / path
        return path
    return BASE_DIR / "data" / "bot.sqlite3"


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db():
        pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_lead(
    session_id: str,
    source: str,
    service: str | None = None,
    contact: str | None = None,
    problem_text: str | None = None,
    agent_summary: str | None = None,
    missing_info: str | None = None,
    status: str = "new",
) -> int:
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO leads (
                session_id, source, service, contact, problem_text,
                agent_summary, missing_info, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                source,
                service,
                contact,
                problem_text,
                agent_summary,
                missing_info,
                status,
                _now(),
            ),
        )
        return int(cur.lastrowid)


def save_feedback(session_id: str, message_text: str) -> int:
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO feedback (session_id, message_text, created_at)
            VALUES (?, ?, ?)
            """,
            (session_id, message_text, _now()),
        )
        return int(cur.lastrowid)


def list_leads() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


def list_feedback() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM feedback ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]
