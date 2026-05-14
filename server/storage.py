"""JSON file storage for Agent Web Review comments."""

from __future__ import annotations

import json
import os
import shutil
import threading
from typing import Optional

from models import Comment

_DATA_DIR_ENV = "AWR_DATA_DIR"
_FILENAME = "comments.json"


def _default_data_dir() -> str:
    env = os.environ.get(_DATA_DIR_ENV)
    if env:
        return env
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


class CommentStorage:
    def __init__(self, data_dir: Optional[str] = None) -> None:
        self._dir = data_dir or _default_data_dir()
        os.makedirs(self._dir, exist_ok=True)
        self._path = os.path.join(self._dir, _FILENAME)
        self._lock = threading.Lock()

    def _read_all(self) -> list[dict]:
        if not os.path.exists(self._path):
            return []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("comments", [])
        except (json.JSONDecodeError, KeyError):
            backup = self._path + ".corrupt"
            shutil.copy2(self._path, backup)
            return []

    def _write_all(self, comments: list[dict]) -> None:
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"comments": comments}, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self._path)

    def get_all(self, page_url: Optional[str] = None, status: Optional[str] = None) -> list[Comment]:
        with self._lock:
            raw = self._read_all()
        if page_url is not None:
            raw = [c for c in raw if c.get("page_url") == page_url]
        if status is not None:
            raw = [c for c in raw if c.get("status") == status]
        raw.sort(key=lambda c: c.get("timestamp", ""), reverse=True)
        return [Comment.from_dict(c) for c in raw]

    def get_by_id(self, comment_id: str) -> Optional[Comment]:
        with self._lock:
            raw = self._read_all()
        for c in raw:
            if c.get("id") == comment_id:
                return Comment.from_dict(c)
        return None

    def create(self, comment: Comment) -> Comment:
        with self._lock:
            raw = self._read_all()
            raw.append(comment.to_dict())
            self._write_all(raw)
        return comment

    def delete(self, comment_id: str) -> bool:
        with self._lock:
            raw = self._read_all()
            new = [c for c in raw if c.get("id") != comment_id]
            if len(new) == len(raw):
                return False
            self._write_all(new)
        return True

    def delete_all(self, page_url: Optional[str] = None, status: Optional[str] = None) -> int:
        if page_url is None and status is None:
            raise ValueError("at least one of page_url or status is required")
        with self._lock:
            raw = self._read_all()
            new = [c for c in raw
                   if not ((page_url is None or c.get("page_url") == page_url) and
                           (status is None or c.get("status") == status))]
            removed = len(raw) - len(new)
            if removed:
                self._write_all(new)
        return removed

    def update_status(self, comment_id: str, new_status: str) -> Optional[Comment]:
        with self._lock:
            raw = self._read_all()
            updated = None
            for i, c in enumerate(raw):
                if c.get("id") == comment_id:
                    raw[i]["status"] = new_status
                    updated = Comment.from_dict(raw[i])
                    break
            if updated is not None:
                self._write_all(raw)
            return updated
