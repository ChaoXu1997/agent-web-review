import pytest


def test_create_mapping(db):
    from app.storage.users import UserStorage
    from app.storage.projects import ProjectMappingStorage
    from app.models import ProjectMappingCreate
    UserStorage(db).create("alice")
    user = UserStorage(db).list_all()[0]
    store = ProjectMappingStorage(db)
    m = store.create(user["id"], ProjectMappingCreate(
        page_url="http://example.com", project_path="/home/user/proj",
    ))
    assert m["id"]
    assert m["user_id"] == user["id"]
    assert m["project_path"] == "/home/user/proj"


def test_create_duplicate_mapping_fails(db):
    from app.storage.users import UserStorage
    from app.storage.projects import ProjectMappingStorage
    from app.models import ProjectMappingCreate
    UserStorage(db).create("alice")
    user = UserStorage(db).list_all()[0]
    store = ProjectMappingStorage(db)
    store.create(user["id"], ProjectMappingCreate(page_url="http://example.com", project_path="/proj"))
    with pytest.raises(ValueError):
        store.create(user["id"], ProjectMappingCreate(page_url="http://example.com", project_path="/other"))


def test_get_urls_by_project_path(db):
    from app.storage.users import UserStorage
    from app.storage.projects import ProjectMappingStorage
    from app.models import ProjectMappingCreate
    UserStorage(db).create("alice")
    user = UserStorage(db).list_all()[0]
    store = ProjectMappingStorage(db)
    store.create(user["id"], ProjectMappingCreate(page_url="http://a.com", project_path="/proj"))
    store.create(user["id"], ProjectMappingCreate(page_url="http://b.com", project_path="/proj"))
    urls = store.get_urls_by_project_path(user["id"], "/proj")
    assert set(urls) == {"http://a.com", "http://b.com"}


def test_get_urls_trailing_slash(db):
    from app.storage.users import UserStorage
    from app.storage.projects import ProjectMappingStorage
    from app.models import ProjectMappingCreate
    UserStorage(db).create("alice")
    user = UserStorage(db).list_all()[0]
    store = ProjectMappingStorage(db)
    store.create(user["id"], ProjectMappingCreate(page_url="http://a.com", project_path="/proj/"))
    urls = store.get_urls_by_project_path(user["id"], "/proj")
    assert urls == ["http://a.com"]


def test_list_all(db):
    from app.storage.users import UserStorage
    from app.storage.projects import ProjectMappingStorage
    from app.models import ProjectMappingCreate
    UserStorage(db).create("alice")
    user = UserStorage(db).list_all()[0]
    store = ProjectMappingStorage(db)
    store.create(user["id"], ProjectMappingCreate(page_url="http://a.com", project_path="/proj"))
    store.create(user["id"], ProjectMappingCreate(page_url="http://b.com", project_path="/other"))
    all_mappings = store.get_all(user["id"])
    assert len(all_mappings) == 2


def test_delete_mapping(db):
    from app.storage.users import UserStorage
    from app.storage.projects import ProjectMappingStorage
    from app.models import ProjectMappingCreate
    UserStorage(db).create("alice")
    user = UserStorage(db).list_all()[0]
    store = ProjectMappingStorage(db)
    store.create(user["id"], ProjectMappingCreate(page_url="http://a.com", project_path="/proj"))
    assert store.delete(user["id"], "http://a.com") is True
    assert len(store.get_all(user["id"])) == 0
