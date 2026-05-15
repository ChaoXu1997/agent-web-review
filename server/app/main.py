from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.db import init_db
from app.auth import set_db
from app.storage.comments import CommentStorage
from app.storage.projects import ProjectMappingStorage
from app.storage.users import UserStorage
from app.mcp.server import create_mcp_server


def create_app(settings: Settings | None = None) -> FastAPI:
    global _app
    settings = settings or Settings()

    os.makedirs(os.path.dirname(settings.database_url), exist_ok=True)
    conn = init_db(settings.database_url)
    set_db(conn)

    app = FastAPI(title="Agent Web Review", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    comment_storage = CommentStorage(conn)
    project_storage = ProjectMappingStorage(conn)
    user_storage = UserStorage(conn)

    app.state.comment_storage = comment_storage
    app.state.project_storage = project_storage
    app.state.user_storage = user_storage
    app.state.admin_token = settings.admin_token
    app.state.db = conn

    from app.routes.comments import router as comments_router
    from app.routes.projects import router as projects_router
    from app.routes.admin import router as admin_router
    from app.routes.sse import router as sse_router

    app.include_router(comments_router)
    app.include_router(projects_router)
    app.include_router(admin_router)
    app.include_router(sse_router)

    @app.get("/api/health")
    def health():
        from app.routes.sse import sse_manager
        return {"status": "ok", "version": "2.0.0", "sse_clients": sse_manager.client_count}

    # Mount MCP sub-app
    mcp_server = create_mcp_server(settings.database_url)
    app.mount("/mcp", mcp_server.streamable_http_app())

    _app = app
    return app


_app: FastAPI | None = None


def get_comment_storage():
    from app.main import _app
    return _app.state.comment_storage


def get_project_storage():
    from app.main import _app
    return _app.state.project_storage


def get_user_storage():
    from app.main import _app
    return _app.state.user_storage


def get_admin_token():
    from app.main import _app
    return _app.state.admin_token


def main():
    global _app
    import uvicorn
    settings = Settings()
    _app = create_app(settings)
    uvicorn.run(_app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
