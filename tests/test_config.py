import os
import tempfile


def test_default_config():
    os.environ.pop("AWR_DATA_DIR", None)
    os.environ.pop("AWR_PORT", None)
    os.environ.pop("AWR_HOST", None)
    from app.config import Settings

    s = Settings()
    assert s.port == 9876
    assert s.host == "127.0.0.1"
    assert "projects.json" in s.mappings_json_path


def test_env_override():
    tmp = tempfile.mkdtemp()
    os.environ["AWR_DATA_DIR"] = tmp
    os.environ["AWR_PORT"] = "8080"
    os.environ["AWR_HOST"] = "0.0.0.0"
    from app.config import Settings

    s = Settings()
    assert s.port == 8080
    assert s.host == "0.0.0.0"
    assert tmp in s.mappings_json_path
    del os.environ["AWR_DATA_DIR"]
    del os.environ["AWR_PORT"]
    del os.environ["AWR_HOST"]
