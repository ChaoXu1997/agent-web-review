from app.models import CommentCreate


def test_create_comment(comment_store):
    c = comment_store.create(
        CommentCreate(
            page_url="http://example.com",
            comment_text="fix the button",
            element_selector="#btn",
        )
    )
    assert c["id"]
    assert c["comment_text"] == "fix the button"
    assert c["status"] == "open"


def test_get_all(comment_store):
    comment_store.create(CommentCreate(page_url="http://a.com", comment_text="c1"))
    comment_store.create(CommentCreate(page_url="http://b.com", comment_text="c2"))
    assert len(comment_store.get_all()) == 2


def test_get_all_with_page_url_filter(comment_store):
    comment_store.create(CommentCreate(page_url="http://a.com", comment_text="c1"))
    comment_store.create(CommentCreate(page_url="http://a.com", comment_text="c2"))
    comment_store.create(CommentCreate(page_url="http://b.com", comment_text="c3"))
    filtered = comment_store.get_all(page_url="http://a.com")
    assert len(filtered) == 2


def test_get_all_status_filter(comment_store):
    c1 = comment_store.create(
        CommentCreate(page_url="http://a.com", comment_text="open one")
    )
    comment_store.update_status(c1["id"], "resolved")
    comment_store.create(
        CommentCreate(page_url="http://a.com", comment_text="still open")
    )
    open_only = comment_store.get_all(status="open")
    assert len(open_only) == 1
    assert open_only[0]["comment_text"] == "still open"


def test_update_status(comment_store):
    created = comment_store.create(
        CommentCreate(page_url="http://a.com", comment_text="resolve me")
    )
    updated = comment_store.update_status(created["id"], "resolved")
    assert updated is not None
    assert updated["status"] == "resolved"


def test_update_status_missing(comment_store):
    assert comment_store.update_status("nonexistent", "resolved") is None


def test_delete_comment(comment_store):
    created = comment_store.create(
        CommentCreate(page_url="http://a.com", comment_text="delete me")
    )
    assert comment_store.delete(created["id"]) is True
    assert len(comment_store.get_all()) == 0


def test_delete_missing(comment_store):
    assert comment_store.delete("nonexistent") is False


def test_delete_all_by_page_url(comment_store):
    comment_store.create(CommentCreate(page_url="http://a.com", comment_text="c1"))
    comment_store.create(CommentCreate(page_url="http://a.com", comment_text="c2"))
    comment_store.create(CommentCreate(page_url="http://b.com", comment_text="keep"))
    count = comment_store.delete_all(page_url="http://a.com")
    assert count == 2
    assert len(comment_store.get_all()) == 1


def test_delete_all_by_status(comment_store):
    c1 = comment_store.create(CommentCreate(page_url="http://a.com", comment_text="c1"))
    comment_store.update_status(c1["id"], "resolved")
    comment_store.create(CommentCreate(page_url="http://a.com", comment_text="c2"))
    count = comment_store.delete_all(status="resolved")
    assert count == 1
    assert all(c["status"] != "resolved" for c in comment_store.get_all())


def test_comment_isolation_between_stores():
    # in-memory: separate storage instances do not share state
    from app.storage.comments import CommentStorage

    s1 = CommentStorage()
    s2 = CommentStorage()
    s1.create(CommentCreate(page_url="http://a.com", comment_text="only in s1"))
    assert len(s1.get_all()) == 1
    assert len(s2.get_all()) == 0
