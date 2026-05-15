from __future__ import annotations

import sqlite3

from app.models import ProjectMappingCreate, new_id


class ProjectMappingStorage:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, user_id: str, data: ProjectMappingCreate) -> dict:
        mid = new_id()
        try:
            self._conn.execute(
                "INSERT INTO project_mappings (id, user_id, page_url, project_path) VALUES (?, ?, ?, ?)",
                (mid, user_id, data.page_url, data.project_path),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"mapping for {data.page_url} already exists for this user")
        return {"id": mid, "user_id": user_id, "page_url": data.page_url, "project_path": data.project_path}

    def get_urls_by_project_path(self, user_id: str, path: str) -> list[str]:
        normalized = path.rstrip("/")
        rows = self._conn.execute(
            "SELECT page_url FROM project_mappings WHERE user_id = ? AND RTRIM(project_path, '/') = ?",
            (user_id, normalized),
        ).fetchall()
        return [r["page_url"] for r in rows]

    def get_all(self, user_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, user_id, page_url, project_path FROM project_mappings WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete(self, user_id: str, page_url: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM project_mappings WHERE user_id = ? AND page_url = ?",
            (user_id, page_url),
        )
        self._conn.commit()
        return cur.rowcount > 0
