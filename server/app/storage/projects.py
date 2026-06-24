from __future__ import annotations

import json
import os
import threading

from app.models import ProjectMappingCreate


def _normalize(path: str) -> str:
    # Normalize the project_path filesystem key so trailing-slash and repeated
    # separator variants collapse to one canonical key. page_url is NOT touched
    # here (URLs are case- and slash-sensitive).
    return os.path.normpath(path)


class ProjectMappingStorage:
    """JSON-file-backed CWD<->URL mapping store.

    Persists across server restarts (Pull model requires stable mapping).
    A single flat list of {page_url, project_path} entries; multiple URLs per
    project path and (by default) one path per URL are both supported.
    """

    def __init__(self, json_path: str) -> None:
        self._path = json_path
        self._lock = threading.Lock()
        self._mappings: list[dict] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("mappings"), list):
                    self._mappings = [
                        m
                        for m in data["mappings"]
                        if isinstance(m, dict)
                        and "page_url" in m
                        and "project_path" in m
                    ]
            except (json.JSONDecodeError, OSError):
                self._mappings = []

    def _persist(self) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"mappings": self._mappings}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path)

    def create(self, data: ProjectMappingCreate) -> dict:
        with self._lock:
            for m in self._mappings:
                if m["page_url"] == data.page_url:
                    raise ValueError(f"mapping for {data.page_url} already exists")
            entry = {"page_url": data.page_url, "project_path": data.project_path}
            self._mappings.append(entry)
            self._persist()
            return dict(entry)

    def get_urls_by_project_path(self, path: str) -> list[str]:
        normalized = _normalize(path)
        with self._lock:
            return [
                m["page_url"]
                for m in self._mappings
                if _normalize(m["project_path"]) == normalized
            ]

    def get_all(self) -> list[dict]:
        with self._lock:
            return [dict(m) for m in self._mappings]

    def delete(self, page_url: str) -> bool:
        with self._lock:
            for i, m in enumerate(self._mappings):
                if m["page_url"] == page_url:
                    self._mappings.pop(i)
                    self._persist()
                    return True
        return False
