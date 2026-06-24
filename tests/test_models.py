from app.models import (
    CommentCreate,
    CommentResponse,
    ProjectMappingCreate,
    ProjectMappingResponse,
)


def test_comment_create():
    c = CommentCreate(
        page_url="http://example.com",
        comment_text="fix the button",
        element_selector="#btn",
    )
    assert c.page_url == "http://example.com"
    assert c.comment_text == "fix the button"
    assert c.element_selector == "#btn"
    assert c.status == "open"


def test_comment_create_defaults():
    c = CommentCreate(page_url="http://example.com", comment_text="hello")
    assert c.element_selector == ""
    assert c.element_xpath == ""
    assert c.status == "open"


def test_comment_response():
    c = CommentResponse(
        id="abc123",
        page_url="http://example.com",
        comment_text="fix",
        timestamp="2026-01-01T00:00:00Z",
        status="open",
    )
    d = c.model_dump()
    assert d["id"] == "abc123"


def test_comment_response_optional_area():
    c = CommentResponse(
        id="abc",
        page_url="http://x.com",
        comment_text="x",
        timestamp="2026-01-01T00:00:00Z",
        status="open",
        area={"x": 10, "y": 20, "width": 100, "height": 50},
    )
    assert c.area is not None


def test_project_mapping_create():
    m = ProjectMappingCreate(page_url="http://a.com", project_path="/home/user/proj")
    assert m.page_url == "http://a.com"
    assert m.project_path == "/home/user/proj"


def test_project_mapping_response():
    m = ProjectMappingResponse(page_url="http://a.com", project_path="/proj")
    assert m.page_url == "http://a.com"
