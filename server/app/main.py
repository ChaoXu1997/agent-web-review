from __future__ import annotations

import contextlib
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

    # Build the MCP server and its streamable-http app first. The session_manager
    # is created lazily by streamable_http_app(), so it must be called before the
    # lifespan references it.
    mcp_server = create_mcp_server()
    mcp_app = mcp_server.streamable_http_app()

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        # Starlette does NOT trigger a mounted sub-app's own lifespan, so the MCP
        # session manager would never start. Run it here from the parent lifespan.
        async with contextlib.AsyncExitStack() as stack:
            await stack.enter_async_context(mcp_server.session_manager.run())
            yield

    app = FastAPI(title="Agent Web Review", version=VERSION, lifespan=lifespan)

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

    # MCP endpoint lives at /mcp inside mcp_app; mounting at "/" lets FastAPI's
    # /api/* routes match first, with /mcp falling through to the MCP app.
    app.mount("/", mcp_app)

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
