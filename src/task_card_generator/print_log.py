"""Local SQLite database tracking printed tasks and app settings."""

import os
import sqlite3
from datetime import datetime
from typing import Optional, Set


class PrintLog:
    """Track printed task IDs and store app settings."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            app_support = os.path.expanduser(
                "~/Library/Application Support/PrintDo"
            )
            os.makedirs(app_support, exist_ok=True)
            db_path = os.path.join(app_support, "printdo.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS printed_tasks (
                things3_id TEXT PRIMARY KEY,
                task_name TEXT,
                printed_at TEXT NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        self.conn.commit()

    def is_printed(self, things3_id: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM printed_tasks WHERE things3_id = ?",
            (things3_id,),
        )
        return cur.fetchone() is not None

    def mark_printed(self, things3_id: str, task_name: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO printed_tasks (things3_id, task_name, printed_at) VALUES (?, ?, ?)",
            (things3_id, task_name, datetime.now().isoformat()),
        )
        self.conn.commit()

    def get_printed_ids(self) -> Set[str]:
        cur = self.conn.execute("SELECT things3_id FROM printed_tasks")
        return {row[0] for row in cur.fetchall()}

    def clear_history(self):
        self.conn.execute("DELETE FROM printed_tasks")
        self.conn.commit()

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        cur = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        row = cur.fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
