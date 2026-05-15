import os
import tempfile


def test_init_db_creates_tables():
    tmp = tempfile.mkdtemp()
    from app.db import init_db
    conn = init_db(os.path.join(tmp, "test.db"))
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    assert "users" in tables
    assert "comments" in tables
    assert "project_mappings" in tables
    conn.close()


def test_init_db_idempotent():
    tmp = tempfile.mkdtemp()
    from app.db import init_db
    path = os.path.join(tmp, "test.db")
    conn1 = init_db(path)
    conn1.close()
    conn2 = init_db(path)
    cur = conn2.execute("SELECT COUNT(*) FROM users")
    assert cur.fetchone()[0] == 0
    conn2.close()


def test_wal_mode():
    tmp = tempfile.mkdtemp()
    from app.db import init_db
    conn = init_db(os.path.join(tmp, "test.db"))
    cur = conn.execute("PRAGMA journal_mode")
    assert cur.fetchone()[0].lower() == "wal"
    conn.close()
