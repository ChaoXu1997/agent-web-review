def test_verify_api_key_success(db):
    from app.storage.users import UserStorage
    from app.auth import verify_api_key
    store = UserStorage(db)
    created = store.create("alice")
    result = verify_api_key(db, created["api_key"])
    assert result is not None
    assert result["id"] == created["id"]


def test_verify_api_key_failure(db):
    from app.auth import verify_api_key
    result = verify_api_key(db, "bad-key")
    assert result is None


def test_verify_admin_token():
    from app.auth import verify_admin_token
    assert verify_admin_token("correct", "correct") is True
    assert verify_admin_token("wrong", "correct") is False
