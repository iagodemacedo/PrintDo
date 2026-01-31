"""Local SQLite database for tracking printed tasks and app state."""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

DB_DIR = Path.home() / "Library" / "Application Support" / "PrintDo"
DB_PATH = DB_DIR / "state.db"


class PrintStateDB:
    """Track which Things 3 tasks have been seen and printed."""

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS seen_tasks (
                things3_id TEXT PRIMARY KEY,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                task_name TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS print_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                things3_id TEXT NOT NULL,
                task_name TEXT DEFAULT '',
                printed_at TEXT NOT NULL,
                template_used TEXT DEFAULT 'default'
            );

            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        self._conn.commit()

    # --- Seen tasks ---

    def mark_seen(self, things3_id: str, task_name: str = "") -> None:
        """Mark a task as seen (appeared in Today list)."""
        now = datetime.now().isoformat()
        self._conn.execute(
            """
            INSERT INTO seen_tasks (things3_id, first_seen, last_seen, task_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(things3_id) DO UPDATE SET last_seen = ?, task_name = ?
            """,
            (things3_id, now, now, task_name, now, task_name),
        )
        self._conn.commit()

    def is_seen(self, things3_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM seen_tasks WHERE things3_id = ?", (things3_id,)
        ).fetchone()
        return row is not None

    def get_all_seen_ids(self) -> set:
        """Get all previously seen task IDs."""
        rows = self._conn.execute("SELECT things3_id FROM seen_tasks").fetchall()
        return {row["things3_id"] for row in rows}

    # --- Print history ---

    def mark_printed(self, things3_id: str, task_name: str = "", template_used: str = "default") -> None:
        """Record that a task was printed."""
        now = datetime.now().isoformat()
        self._conn.execute(
            "INSERT INTO print_history (things3_id, task_name, printed_at, template_used) VALUES (?, ?, ?, ?)",
            (things3_id, task_name, now, template_used),
        )
        self._conn.commit()

    def is_printed(self, things3_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM print_history WHERE things3_id = ?", (things3_id,)
        ).fetchone()
        return row is not None

    def get_print_history(self, limit: int = 50) -> List[dict]:
        rows = self._conn.execute(
            "SELECT * FROM print_history ORDER BY printed_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Preferences ---

    def set_pref(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO preferences (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, value, value),
        )
        self._conn.commit()

    def get_pref(self, key: str, default: str = "") -> str:
        row = self._conn.execute(
            "SELECT value FROM preferences WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def close(self):
        self._conn.close()
