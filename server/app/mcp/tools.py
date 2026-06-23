from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from mcp.server.fastmcp import Context

from app.storage.comments import CommentStorage
from app.storage.projects import ProjectMappingStorage


def _comment_store(ctx: Context) -> CommentStorage:
    app: FastAPI = ctx.request_context.lifespan_context.app
    return app.state.comment_storage


def _project_store(ctx: Context) -> ProjectMappingStorage:
    app: FastAPI = ctx.request_context.lifespan_context.app
    return app.state.project_storage


def register_tools(server) -> None:

    @server.tool()
    def awr_get_comments(
        page_url: Optional[str] = None,
        status: Optional[str] = None,
        project_path: Optional[str] = None,
        ctx: Context = None,
    ) -> list[dict]:
        """Get review comments, optionally filtered by page_url, status, and/or project_path.

        project_path reverse-resolves CWD->page_url mappings (multi-URL supported).
        """
        store = _comment_store(ctx)
        if project_path:
            proj_store = _project_store(ctx)
            urls = set(proj_store.get_urls_by_project_path(project_path))
            if not urls:
                return []
            comments = store.get_all(status=status)
            comments = [c for c in comments if c["page_url"] in urls]
            if page_url:
                comments = [c for c in comments if c["page_url"] == page_url]
            return comments
        return store.get_all(page_url=page_url, status=status)

    @server.tool()
    def awr_resolve_comment(comment_id: str, ctx: Context = None) -> dict:
        """Mark a comment as resolved by ID."""
        store = _comment_store(ctx)
        updated = store.update_status(comment_id, "resolved")
        if not updated:
            return {"error": "Comment not found", "comment_id": comment_id}
        from app.routes.sse import sse_manager

        sse_manager.broadcast("comment_resolved", updated)
        return updated

    @server.tool()
    def awr_delete_comment(comment_id: str, ctx: Context = None) -> dict:
        """Delete a comment by ID."""
        store = _comment_store(ctx)
        if not store.delete(comment_id):
            return {"error": "Comment not found", "comment_id": comment_id}
        return {"deleted": True}
