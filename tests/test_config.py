import os
import tempfile


def test_default_config():
    os.environ.pop("AWR_DATA_DIR", None)
    os.environ.pop("AWR_ADMIN_TOKEN", None)
    os.environ.pop("AWR_PORT", None)
    from app.config import Settings
    s = Settings()
    assert s.port == 9876
    assert s.admin_token == ""
    assert "awr.db" in s.database_url


def test_env_override():
    tmp = tempfile.mkdtemp()
    os.environ["AWR_DATA_DIR"] = tmp
    os.environ["AWR_ADMIN_TOKEN"] = "my-secret"
    os.environ["AWR_PORT"] = "8080"
    from app.config import Settings
    s = Settings()
    assert s.port == 8080
    assert s.admin_token == "my-secret"
    assert tmp in s.database_url
    del os.environ["AWR_DATA_DIR"]
    del os.environ["AWR_ADMIN_TOKEN"]
    del os.environ["AWR_PORT"]
