import os
import tempfile

import pytest

from app.models import ProjectMappingCreate
from app.storage.projects import ProjectMappingStorage


def _store_in_tmp():
    tmp = tempfile.mkdtemp()
    return ProjectMappingStorage(os.path.join(tmp, "projects.json")), tmp


def test_create_mapping(project_store):
    m = project_store.create(
        ProjectMappingCreate(
            page_url="http://example.com",
            project_path="/home/user/proj",
        )
    )
    assert m["page_url"] == "http://example.com"
    assert m["project_path"] == "/home/user/proj"


def test_create_duplicate_mapping_fails(project_store):
    project_store.create(
        ProjectMappingCreate(page_url="http://example.com", project_path="/proj")
    )
    with pytest.raises(ValueError):
        project_store.create(
            ProjectMappingCreate(page_url="http://example.com", project_path="/other")
        )


def test_get_urls_by_project_path(project_store):
    project_store.create(
        ProjectMappingCreate(page_url="http://a.com", project_path="/proj")
    )
    project_store.create(
        ProjectMappingCreate(page_url="http://b.com", project_path="/proj")
    )
    urls = project_store.get_urls_by_project_path("/proj")
    assert set(urls) == {"http://a.com", "http://b.com"}


def test_get_urls_trailing_slash(project_store):
    project_store.create(
        ProjectMappingCreate(page_url="http://a.com", project_path="/proj/")
    )
    urls = project_store.get_urls_by_project_path("/proj")
    assert urls == ["http://a.com"]


def test_get_urls_collapses_redundant_separators(project_store):
    # normpath collapses "//" and trailing "/" so all these resolve to one key.
    project_store.create(
        ProjectMappingCreate(page_url="http://a.com", project_path="/proj")
    )
    project_store.create(
        ProjectMappingCreate(page_url="http://b.com", project_path="/proj//")
    )
    project_store.create(
        ProjectMappingCreate(page_url="http://c.com", project_path="/proj/sub/..")
    )
    urls = project_store.get_urls_by_project_path("/proj/")
    assert set(urls) == {"http://a.com", "http://b.com", "http://c.com"}


def test_list_all(project_store):
    project_store.create(
        ProjectMappingCreate(page_url="http://a.com", project_path="/proj")
    )
    project_store.create(
        ProjectMappingCreate(page_url="http://b.com", project_path="/other")
    )
    all_mappings = project_store.get_all()
    assert len(all_mappings) == 2


def test_delete_mapping(project_store):
    project_store.create(
        ProjectMappingCreate(page_url="http://a.com", project_path="/proj")
    )
    assert project_store.delete("http://a.com") is True
    assert len(project_store.get_all()) == 0


def test_delete_missing(project_store):
    assert project_store.delete("http://nope.com") is False


def test_persists_across_instances():
    store1, tmp = _store_in_tmp()
    store1.create(ProjectMappingCreate(page_url="http://a.com", project_path="/proj"))
    store1.create(ProjectMappingCreate(page_url="http://b.com", project_path="/proj"))

    # New instance loading the same file
    store2 = ProjectMappingStorage(os.path.join(tmp, "projects.json"))
    urls = store2.get_urls_by_project_path("/proj")
    assert set(urls) == {"http://a.com", "http://b.com"}


def test_multiple_paths_per_url_set():
    # multi CWD<->URL: different projects, different URLs
    store, _ = _store_in_tmp()
    store.create(
        ProjectMappingCreate(page_url="http://localhost:5173", project_path="/proj1")
    )
    store.create(
        ProjectMappingCreate(page_url="http://localhost:3000", project_path="/proj2")
    )
    assert set(store.get_urls_by_project_path("/proj1")) == {"http://localhost:5173"}
    assert set(store.get_urls_by_project_path("/proj2")) == {"http://localhost:3000"}


def test_corrupt_json_treated_as_empty():
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "projects.json")
    with open(path, "w") as f:
        f.write("{not valid json")
    store = ProjectMappingStorage(path)
    assert store.get_all() == []
