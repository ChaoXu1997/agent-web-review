import os
import tempfile
import shutil

import pytest


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def admin_token():
    return "test-admin-token"


@pytest.fixture
def db(tmp_dir):
    from app.db import init_db
    conn = init_db(os.path.join(tmp_dir, "test.db"))
    yield conn
    conn.close()
