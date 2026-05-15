from __future__ import annotations

import json
import sqlite3
from typing import Optional

from app.models import CommentCreate, new_id, now_iso


class CommentStorage:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, user_id: str, data: CommentCreate) -> dict:
        cid = new_id()
        ts = now_iso()
        area_json = json.dumps(data.area) if data.area else None
        self._conn.execute(
            """INSERT INTO comments
               (id, user_id, page_url, comment_text, element_selector,
                element_xpath, element_text, element_html, screenshot_b64,
                area, timestamp, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cid, user_id, data.page_url, data.comment_text,
             data.element_selector, data.element_xpath, data.element_text,
             data.element_html, data.screenshot_b64, area_json, ts, data.status),
        )
        self._conn.commit()
        return self._get_by_id(cid)

    def get_all(
        self,
        user_id: str,
        page_url: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict]:
        query = "SELECT * FROM comments WHERE user_id = ?"
        params: list = [user_id]
        if page_url is not None:
            query += " AND page_url = ?"
            params.append(page_url)
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY timestamp"
        rows = self._conn.execute(query, params).fetchall()
        return [_row_to_dict(r) for r in rows]

    def update_status(self, user_id: str, comment_id: str, new_status: str) -> Optional[dict]:
        self._conn.execute(
            "UPDATE comments SET status = ? WHERE id = ? AND user_id = ?",
            (new_status, comment_id, user_id),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM comments WHERE id = ? AND user_id = ?",
            (comment_id, user_id),
        ).fetchone()
        return _row_to_dict(row) if row else None

    def delete(self, user_id: str, comment_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM comments WHERE id = ? AND user_id = ?",
            (comment_id, user_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def delete_all(
        self,
        user_id: str,
        page_url: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        query = "DELETE FROM comments WHERE user_id = ?"
        params: list = [user_id]
        if page_url is not None:
            query += " AND page_url = ?"
            params.append(page_url)
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        cur = self._conn.execute(query, params)
        self._conn.commit()
        return cur.rowcount

    def _get_by_id(self, comment_id: str) -> Optional[dict]:
        row = self._conn.execute("SELECT * FROM comments WHERE id = ?", (comment_id,)).fetchone()
        return _row_to_dict(row) if row else None


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    if d.get("area") and isinstance(d["area"], str):
        d["area"] = json.loads(d["area"])
    return d
