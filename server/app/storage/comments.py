from __future__ import annotations

import threading
from typing import Optional

from app.models import CommentCreate, new_id, now_iso


class CommentStorage:
    """In-memory comment store, grouped by page_url.

    State lives only for the server process lifetime (restart loses data, as intended).
    Thread-safe via a single coarse-grained lock.
    """

    def __init__(self) -> None:
        self._comments: list[dict] = []
        self._lock = threading.Lock()

    def create(self, data: CommentCreate) -> dict:
        cid = new_id()
        ts = now_iso()
        comment = {
            "id": cid,
            "page_url": data.page_url,
            "comment_text": data.comment_text,
            "element_selector": data.element_selector,
            "element_xpath": data.element_xpath,
            "element_text": data.element_text,
            "element_html": data.element_html,
            "screenshot_b64": data.screenshot_b64,
            "area": data.area,
            "timestamp": ts,
            "status": data.status,
        }
        with self._lock:
            self._comments.append(comment)
        return comment

    def get_all(
        self,
        page_url: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict]:
        with self._lock:
            snapshot = list(self._comments)
        result = snapshot
        if page_url is not None:
            result = [c for c in result if c["page_url"] == page_url]
        if status is not None:
            result = [c for c in result if c["status"] == status]
        result = sorted(result, key=lambda c: c["timestamp"])
        return result

    def update_status(self, comment_id: str, new_status: str) -> Optional[dict]:
        with self._lock:
            for c in self._comments:
                if c["id"] == comment_id:
                    c["status"] = new_status
                    return dict(c)
        return None

    def delete(self, comment_id: str) -> bool:
        with self._lock:
            for i, c in enumerate(self._comments):
                if c["id"] == comment_id:
                    self._comments.pop(i)
                    return True
        return False

    def delete_all(
        self,
        page_url: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        with self._lock:
            original = len(self._comments)
            kept = []
            for c in self._comments:
                if page_url is not None and c["page_url"] != page_url:
                    kept.append(c)
                    continue
                if status is not None and c["status"] != status:
                    kept.append(c)
                    continue
                # matches filter -> delete
            self._comments = kept
            return original - len(kept)
