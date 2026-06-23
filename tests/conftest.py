import os
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def settings(tmp_dir):
    return Settings(data_dir=tmp_dir)


@pytest.fixture
def app(settings):
    import app.main as main_mod

    application = create_app(settings)
    main_mod._app = application
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def comment_store(app):
    return app.state.comment_storage


@pytest.fixture
def project_store(app):
    return app.state.project_storage
