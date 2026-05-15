"""JSON file storage for Agent Web Review project path mappings."""

from __future__ import annotations

import json
import os
import shutil
import threading
from typing import Optional

_FILENAME = "projects.json"


def _default_data_dir() -> str:
    env = os.environ.get("AWR_DATA_DIR")
    if env:
        return env
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


class ProjectMappingStorage:
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
            return data.get("mappings", [])
        except (json.JSONDecodeError, KeyError):
            backup = self._path + ".corrupt"
            shutil.copy2(self._path, backup)
            return []

    def _write_all(self, mappings: list[dict]) -> None:
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"mappings": mappings}, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self._path)

    def get_all(self) -> list[dict]:
        with self._lock:
            return list(self._read_all())

    def get_urls_by_project_path(self, path: str) -> list[str]:
        """Return all page_url values whose project_path matches, with trailing-slash normalization."""
        normalized = path.rstrip("/")
        mappings = self.get_all()
        return [
            m["page_url"]
            for m in mappings
            if m["project_path"].rstrip("/") == normalized
        ]

    def create(self, mapping: dict) -> dict:
        with self._lock:
            raw = self._read_all()
            for existing in raw:
                if existing["page_url"] == mapping["page_url"]:
                    raise ValueError(f"mapping for {mapping['page_url']} already exists")
            raw.append({
                "page_url": mapping["page_url"],
                "project_path": mapping["project_path"],
            })
            self._write_all(raw)
        return mapping

    def delete_all(self) -> None:
        with self._lock:
            self._write_all([])

    def delete(self, page_url: str) -> bool:
        with self._lock:
            raw = self._read_all()
            new = [m for m in raw if m["page_url"] != page_url]
            if len(new) == len(raw):
                return False
            self._write_all(new)
        return True
