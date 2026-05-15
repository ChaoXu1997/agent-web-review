def test_create_comment(db):
    from app.storage.users import UserStorage
    from app.storage.comments import CommentStorage
    from app.models import CommentCreate
    UserStorage(db).create("alice")
    user = UserStorage(db).list_all()[0]
    store = CommentStorage(db)
    c = store.create(user["id"], CommentCreate(
        page_url="http://example.com",
        comment_text="fix the button",
        element_selector="#btn",
    ))
    assert c["id"]
    assert c["user_id"] == user["id"]
    assert c["comment_text"] == "fix the button"
    assert c["status"] == "open"


def test_get_all_by_user(db):
    from app.storage.users import UserStorage
    from app.storage.comments import CommentStorage
    from app.models import CommentCreate
    UserStorage(db).create("alice")
    UserStorage(db).create("bob")
    users = UserStorage(db).list_all()
    alice, bob = users[0], users[1]
    store = CommentStorage(db)
    store.create(alice["id"], CommentCreate(page_url="http://a.com", comment_text="alice comment"))
    store.create(bob["id"], CommentCreate(page_url="http://b.com", comment_text="bob comment"))
    alice_comments = store.get_all(alice["id"])
    assert len(alice_comments) == 1
    assert alice_comments[0]["comment_text"] == "alice comment"


def test_get_all_with_page_url_filter(db):
    from app.storage.users import UserStorage
    from app.storage.comments import CommentStorage
    from app.models import CommentCreate
    UserStorage(db).create("alice")
    user = UserStorage(db).list_all()[0]
    store = CommentStorage(db)
    store.create(user["id"], CommentCreate(page_url="http://a.com", comment_text="c1"))
    store.create(user["id"], CommentCreate(page_url="http://a.com", comment_text="c2"))
    store.create(user["id"], CommentCreate(page_url="http://b.com", comment_text="c3"))
    filtered = store.get_all(user["id"], page_url="http://a.com")
    assert len(filtered) == 2


def test_get_all_status_filter(db):
    from app.storage.users import UserStorage
    from app.storage.comments import CommentStorage
    from app.models import CommentCreate
    UserStorage(db).create("alice")
    user = UserStorage(db).list_all()[0]
    store = CommentStorage(db)
    c1 = store.create(user["id"], CommentCreate(page_url="http://a.com", comment_text="open one"))
    store.update_status(user["id"], c1["id"], "resolved")
    store.create(user["id"], CommentCreate(page_url="http://a.com", comment_text="still open"))
    open_only = store.get_all(user["id"], status="open")
    assert len(open_only) == 1
    assert open_only[0]["comment_text"] == "still open"


def test_update_status(db):
    from app.storage.users import UserStorage
    from app.storage.comments import CommentStorage
    from app.models import CommentCreate
    UserStorage(db).create("alice")
    user = UserStorage(db).list_all()[0]
    store = CommentStorage(db)
    created = store.create(user["id"], CommentCreate(page_url="http://a.com", comment_text="resolve me"))
    updated = store.update_status(user["id"], created["id"], "resolved")
    assert updated is not None
    assert updated["status"] == "resolved"


def test_update_status_wrong_user(db):
    from app.storage.users import UserStorage
    from app.storage.comments import CommentStorage
    from app.models import CommentCreate
    UserStorage(db).create("alice")
    UserStorage(db).create("bob")
    users = UserStorage(db).list_all()
    store = CommentStorage(db)
    created = store.create(users[0]["id"], CommentCreate(page_url="http://a.com", comment_text="mine"))
    result = store.update_status(users[1]["id"], created["id"], "resolved")
    assert result is None


def test_delete_comment(db):
    from app.storage.users import UserStorage
    from app.storage.comments import CommentStorage
    from app.models import CommentCreate
    UserStorage(db).create("alice")
    user = UserStorage(db).list_all()[0]
    store = CommentStorage(db)
    created = store.create(user["id"], CommentCreate(page_url="http://a.com", comment_text="delete me"))
    assert store.delete(user["id"], created["id"]) is True
    assert len(store.get_all(user["id"])) == 0


def test_delete_wrong_user(db):
    from app.storage.users import UserStorage
    from app.storage.comments import CommentStorage
    from app.models import CommentCreate
    UserStorage(db).create("alice")
    UserStorage(db).create("bob")
    users = UserStorage(db).list_all()
    store = CommentStorage(db)
    created = store.create(users[0]["id"], CommentCreate(page_url="http://a.com", comment_text="mine"))
    assert store.delete(users[1]["id"], created["id"]) is False


def test_delete_all_by_page_url(db):
    from app.storage.users import UserStorage
    from app.storage.comments import CommentStorage
    from app.models import CommentCreate
    UserStorage(db).create("alice")
    user = UserStorage(db).list_all()[0]
    store = CommentStorage(db)
    store.create(user["id"], CommentCreate(page_url="http://a.com", comment_text="c1"))
    store.create(user["id"], CommentCreate(page_url="http://a.com", comment_text="c2"))
    store.create(user["id"], CommentCreate(page_url="http://b.com", comment_text="keep"))
    count = store.delete_all(user["id"], page_url="http://a.com")
    assert count == 2
    assert len(store.get_all(user["id"])) == 1
