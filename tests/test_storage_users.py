def test_create_user(db):
    from app.storage.users import UserStorage
    store = UserStorage(db)
    user = store.create("alice")
    assert user["name"] == "alice"
    assert len(user["api_key"]) >= 32
    assert user["id"]


def test_create_user_same_name_ok(db):
    from app.storage.users import UserStorage
    store = UserStorage(db)
    u1 = store.create("alice")
    u2 = store.create("alice")
    assert u1["id"] != u2["id"]


def test_get_by_api_key(db):
    from app.storage.users import UserStorage
    store = UserStorage(db)
    created = store.create("bob")
    found = store.get_by_api_key(created["api_key"])
    assert found is not None
    assert found["id"] == created["id"]


def test_get_by_api_key_not_found(db):
    from app.storage.users import UserStorage
    store = UserStorage(db)
    assert store.get_by_api_key("nonexistent") is None


def test_list_users(db):
    from app.storage.users import UserStorage
    store = UserStorage(db)
    store.create("alice")
    store.create("bob")
    users = store.list_all()
    assert len(users) == 2
    names = {u["name"] for u in users}
    assert names == {"alice", "bob"}


def test_delete_user(db):
    from app.storage.users import UserStorage
    store = UserStorage(db)
    created = store.create("charlie")
    assert store.delete(created["id"]) is True
    assert store.get_by_api_key(created["api_key"]) is None


def test_delete_user_not_found(db):
    from app.storage.users import UserStorage
    store = UserStorage(db)
    assert store.delete("nonexistent") is False
