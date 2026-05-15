def test_comment_create():
    from app.models import CommentCreate
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
    from app.models import CommentCreate
    c = CommentCreate(page_url="http://example.com", comment_text="hello")
    assert c.element_selector == ""
    assert c.element_xpath == ""
    assert c.status == "open"


def test_comment_response():
    from app.models import CommentResponse
    c = CommentResponse(
        id="abc123", user_id="u1", page_url="http://example.com",
        comment_text="fix", timestamp="2026-01-01T00:00:00Z", status="open",
    )
    d = c.model_dump()
    assert d["id"] == "abc123"
    assert d["user_id"] == "u1"


def test_comment_response_optional_area():
    from app.models import CommentResponse
    c = CommentResponse(
        id="abc", user_id="u1", page_url="http://x.com",
        comment_text="x", timestamp="2026-01-01T00:00:00Z", status="open",
        area={"x": 10, "y": 20, "width": 100, "height": 50},
    )
    assert c.area is not None


def test_user_response():
    from app.models import UserResponse
    u = UserResponse(id="u1", name="alice", api_key="key1", created_at="2026-01-01T00:00:00Z")
    d = u.model_dump()
    assert d["name"] == "alice"
    assert "api_key" in d


def test_project_mapping_create():
    from app.models import ProjectMappingCreate
    m = ProjectMappingCreate(page_url="http://a.com", project_path="/home/user/proj")
    assert m.page_url == "http://a.com"
    assert m.project_path == "/home/user/proj"


def test_project_mapping_response():
    from app.models import ProjectMappingResponse
    m = ProjectMappingResponse(id="p1", user_id="u1", page_url="http://a.com", project_path="/proj")
    assert m.user_id == "u1"
