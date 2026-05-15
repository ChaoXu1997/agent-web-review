from __future__ import annotations

import sqlite3


_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    api_key    TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comments (
    id               TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL REFERENCES users(id),
    page_url         TEXT NOT NULL,
    comment_text     TEXT NOT NULL,
    element_selector TEXT DEFAULT '',
    element_xpath    TEXT DEFAULT '',
    element_text     TEXT DEFAULT '',
    element_html     TEXT DEFAULT '',
    screenshot_b64   TEXT DEFAULT '',
    area             TEXT,
    timestamp        TEXT NOT NULL,
    status           TEXT DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS project_mappings (
    id           TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL REFERENCES users(id),
    page_url     TEXT NOT NULL,
    project_path TEXT NOT NULL,
    UNIQUE(user_id, page_url)
);

CREATE INDEX IF NOT EXISTS idx_comments_user_status
    ON comments(user_id, status);
CREATE INDEX IF NOT EXISTS idx_comments_page_url
    ON comments(user_id, page_url);
CREATE INDEX IF NOT EXISTS idx_project_mappings_user
    ON project_mappings(user_id);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn
