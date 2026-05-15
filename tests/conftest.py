import os
import tempfile
import shutil

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import init_db
from app.main import create_app


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def admin_token():
    return "test-admin-token"


@pytest.fixture
def settings(tmp_dir, admin_token):
    return Settings(
        data_dir=tmp_dir,
        admin_token=admin_token,
    )


@pytest.fixture
def app(settings):
    import app.main as main_mod
    app = create_app(settings)
    main_mod._app = app
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def db(app):
    return app.state.db


@pytest.fixture
def user_with_key(client, admin_token):
    resp = client.post(
        "/admin/keys",
        json={"name": "tester"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    return resp.json()


@pytest.fixture
def auth_headers(user_with_key):
    return {"Authorization": f"Bearer {user_with_key['api_key']}"}
