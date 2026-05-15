from __future__ import annotations

import sqlite3
from typing import Optional

from fastapi import Depends, HTTPException, Header


def verify_api_key(db: sqlite3.Connection, api_key: str) -> Optional[dict]:
    if not api_key:
        return None
    cur = db.execute(
        "SELECT id, name, api_key, created_at FROM users WHERE api_key = ?",
        (api_key,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def verify_admin_token(provided: str, expected: str) -> bool:
    return provided == expected and bool(expected)


# Module-level DB accessor — will be wired in main.py
_db_instance: sqlite3.Connection | None = None


def set_db(conn: sqlite3.Connection) -> None:
    global _db_instance
    _db_instance = conn


def _get_db() -> sqlite3.Connection:
    if _db_instance is None:
        raise RuntimeError("DB not initialized")
    return _db_instance


def get_current_user(
    authorization: str = Header(default=""),
    db: sqlite3.Connection = Depends(_get_db),
) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[len("Bearer "):]
    user = verify_api_key(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user
