"""Local SQLite storage for translation project history."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path("app.db")


def _connect() -> sqlite3.Connection:
    """Create a SQLite connection with dictionary-like rows."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _utc_now() -> str:
    """Return an ISO timestamp suitable for local history records."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db() -> None:
    """Create the local SQLite database and translation history table."""
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS translation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_title TEXT,
                target_article_title TEXT,
                source_language TEXT,
                target_language TEXT,
                provider TEXT,
                source_wikitext TEXT,
                translated_wikitext TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )


def save_translation_project(
    *,
    article_title: str,
    target_article_title: str,
    source_language: str,
    target_language: str,
    provider: str,
    source_wikitext: str,
    translated_wikitext: str,
) -> int:
    """
    Save a translation project as a new history row.

    Phase 6A intentionally inserts a new record on every save.
    """
    now = _utc_now()
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO translation_history (
                article_title,
                target_article_title,
                source_language,
                target_language,
                provider,
                source_wikitext,
                translated_wikitext,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article_title,
                target_article_title,
                source_language,
                target_language,
                provider,
                source_wikitext,
                translated_wikitext,
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)


def get_all_projects() -> list[dict[str, Any]]:
    """Return all saved projects, newest first."""
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                article_title,
                target_article_title,
                source_language,
                target_language,
                provider,
                created_at,
                updated_at
            FROM translation_history
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_project_by_id(project_id: int) -> dict[str, Any] | None:
    """Return one saved project by id."""
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                article_title,
                target_article_title,
                source_language,
                target_language,
                provider,
                source_wikitext,
                translated_wikitext,
                created_at,
                updated_at
            FROM translation_history
            WHERE id = ?
            """,
            (project_id,),
        ).fetchone()
    return dict(row) if row else None


def delete_project(project_id: int) -> None:
    """Delete a saved project by id."""
    with _connect() as connection:
        connection.execute("DELETE FROM translation_history WHERE id = ?", (project_id,))
