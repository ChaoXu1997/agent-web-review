from app.storage.comments import CommentStorage
from app.storage.projects import ProjectMappingStorage
from app.models import CommentCreate, ProjectMappingCreate


def test_mcp_create_server():
    from mcp.server.fastmcp import FastMCP
    from app.mcp.server import create_mcp_server
    from fastapi import FastAPI

    app = FastAPI()
    app.state.comment_storage = CommentStorage()
    app.state.project_storage = ProjectMappingStorage("/tmp/nonexistent-awr-test.json")
    server = create_mcp_server(app=app)
    assert isinstance(server, FastMCP)


def test_mcp_get_comments_by_project_path(tmp_path, monkeypatch):
    """awr_get_comments resolves CWD->URL via project mappings, no auth needed."""
    from fastapi import FastAPI

    comment_store = CommentStorage()
    project_store = ProjectMappingStorage(str(tmp_path / "projects.json"))
    project_store.create(
        ProjectMappingCreate(
            page_url="http://localhost:5173", project_path="/home/me/proj"
        )
    )
    comment_store.create(
        CommentCreate(page_url="http://localhost:5173", comment_text="fix nav")
    )
    comment_store.create(
        CommentCreate(page_url="http://other.com", comment_text="unrelated")
    )

    app = FastAPI()
    app.state.comment_storage = comment_store
    app.state.project_storage = project_store

    from app.mcp.tools import register_tools

    class FakeLifespan:
        def __init__(self, app_):
            self.app = app_

    class FakeReqCtx:
        def __init__(self, app_):
            self.lifespan_context = FakeLifespan(app_)
            self.meta = {}

    class FakeCtx:
        def __init__(self, app_):
            self.request_context = FakeReqCtx(app_)

    captured = {}

    class FakeServer:
        def tool(self):
            def deco(fn):
                captured[fn.__name__] = fn
                return fn

            return deco

    register_tools(FakeServer())
    ctx = FakeCtx(app)

    result = captured["awr_get_comments"](project_path="/home/me/proj", ctx=ctx)
    assert len(result) == 1
    assert result[0]["comment_text"] == "fix nav"


def test_mcp_resolve_comment_no_auth(tmp_path):
    from fastapi import FastAPI

    comment_store = CommentStorage()
    app = FastAPI()
    app.state.comment_storage = comment_store
    app.state.project_storage = ProjectMappingStorage(str(tmp_path / "p.json"))

    created = comment_store.create(
        CommentCreate(page_url="http://a.com", comment_text="x")
    )

    from app.mcp.tools import register_tools

    class FakeLifespan:
        def __init__(self, app_):
            self.app = app_

    class FakeReqCtx:
        def __init__(self, app_):
            self.lifespan_context = FakeLifespan(app_)
            self.meta = {}

    class FakeCtx:
        def __init__(self, app_):
            self.request_context = FakeReqCtx(app_)

    captured = {}

    class FakeServer:
        def tool(self):
            def deco(fn):
                captured[fn.__name__] = fn
                return fn

            return deco

    register_tools(FakeServer())
    ctx = FakeCtx(app)
    out = captured["awr_resolve_comment"](comment_id=created["id"], ctx=ctx)
    assert out["status"] == "resolved"

    out_missing = captured["awr_resolve_comment"](comment_id="nope", ctx=ctx)
    assert "error" in out_missing
