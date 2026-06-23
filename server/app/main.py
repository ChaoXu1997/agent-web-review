from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.storage.comments import CommentStorage
from app.storage.projects import ProjectMappingStorage
from app.mcp.server import create_mcp_server

VERSION = "2.1.0"


def create_app(settings: Settings | None = None) -> FastAPI:
    global _app
    settings = settings or Settings()

    os.makedirs(os.path.dirname(settings.mappings_json_path), exist_ok=True)

    app = FastAPI(title="Agent Web Review", version=VERSION)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    comment_storage = CommentStorage()
    project_storage = ProjectMappingStorage(settings.mappings_json_path)

    app.state.comment_storage = comment_storage
    app.state.project_storage = project_storage

    from app.routes.comments import router as comments_router
    from app.routes.projects import router as projects_router
    from app.routes.sse import router as sse_router

    app.include_router(comments_router)
    app.include_router(projects_router)
    app.include_router(sse_router)

    @app.get("/api/health")
    def health():
        from app.routes.sse import sse_manager

        return {
            "status": "ok",
            "version": VERSION,
            "sse_clients": sse_manager.client_count,
        }

    # Mount MCP sub-app (auth-free)
    mcp_server = create_mcp_server(app=app)
    app.mount("/mcp", mcp_server.streamable_http_app())

    _app = app
    return app


_app: FastAPI | None = None


def get_comment_storage() -> CommentStorage:
    from app.main import _app

    return _app.state.comment_storage


def get_project_storage() -> ProjectMappingStorage:
    from app.main import _app

    return _app.state.project_storage


def main():
    global _app
    import uvicorn

    settings = Settings()
    _app = create_app(settings)
    uvicorn.run(_app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
