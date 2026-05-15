from __future__ import annotations

import secrets
import sqlite3
from typing import Optional

from app.models import new_id, now_iso


class UserStorage:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, name: str) -> dict:
        uid = new_id()
        key = secrets.token_hex(32)
        ts = now_iso()
        self._conn.execute(
            "INSERT INTO users (id, name, api_key, created_at) VALUES (?, ?, ?, ?)",
            (uid, name, key, ts),
        )
        self._conn.commit()
        return {"id": uid, "name": name, "api_key": key, "created_at": ts}

    def get_by_api_key(self, api_key: str) -> Optional[dict]:
        cur = self._conn.execute(
            "SELECT id, name, api_key, created_at FROM users WHERE api_key = ?",
            (api_key,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)

    def list_all(self) -> list[dict]:
        cur = self._conn.execute("SELECT id, name, api_key, created_at FROM users ORDER BY created_at")
        return [dict(row) for row in cur.fetchall()]

    def delete(self, user_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self._conn.commit()
        return cur.rowcount > 0
