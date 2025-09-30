from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    retries INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class QueueManager:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._ensure_db()

    def enqueue(self, task_type: str, payload: Dict) -> None:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO tasks(task_type, payload) VALUES (?, ?)",
                (task_type, json.dumps(payload)),
            )
            conn.commit()

    def next_task(self) -> Optional[Tuple[int, str, Dict, int]]:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT id, task_type, payload, retries FROM tasks ORDER BY id LIMIT 1"
            ).fetchone()
            if not row:
                return None
            payload = json.loads(row[2])
            return row[0], row[1], payload, row[3]

    def pending_count(self) -> int:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            row = conn.execute("SELECT COUNT(1) FROM tasks").fetchone()
            return int(row[0]) if row else 0

    def mark_success(self, task_id: int) -> None:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()

    def mark_failure(self, task_id: int, error: str) -> None:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "UPDATE tasks SET retries = retries + 1, last_error = ? WHERE id = ?",
                (error[:500], task_id),
            )
            conn.commit()

    def _ensure_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(DB_SCHEMA)
            conn.commit()


__all__ = ["QueueManager"]
