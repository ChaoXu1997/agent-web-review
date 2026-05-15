from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP, Context

from app.db import init_db
from app.auth import verify_api_key
from app.storage.comments import CommentStorage
from app.storage.projects import ProjectMappingStorage


def _get_user_from_ctx(ctx: Context) -> dict:
    try:
        headers = ctx.request_context.meta.get("headers", {}) if ctx.request_context.meta else {}
        auth_header = headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
            db_path = ctx.request_context.lifespan_context.db_path
            conn = init_db(db_path)
            try:
                user = verify_api_key(conn, token)
                if user:
                    return user
            finally:
                conn.close()
    except Exception:
        pass
    return {}


def register_tools(server: FastMCP) -> None:

    @server.tool()
    def awr_get_comments(
        page_url: Optional[str] = None,
        status: Optional[str] = None,
        project_path: Optional[str] = None,
        ctx: Context = None,
    ) -> list[dict]:
        """Get review comments, optionally filtered by page_url, status, and/or project_path."""
        db_path = ctx.request_context.lifespan_context.db_path
        conn = init_db(db_path)
        try:
            user = _get_user_from_ctx(ctx)
            if not user:
                return []
            store = CommentStorage(conn)
            if project_path:
                proj_store = ProjectMappingStorage(conn)
                urls = proj_store.get_urls_by_project_path(user["id"], project_path)
                if not urls:
                    return []
                url_set = set(urls)
                comments = store.get_all(user["id"], status=status)
                comments = [c for c in comments if c["page_url"] in url_set]
                if page_url:
                    comments = [c for c in comments if c["page_url"] == page_url]
                return comments
            return store.get_all(user["id"], page_url=page_url, status=status)
        finally:
            conn.close()

    @server.tool()
    def awr_resolve_comment(comment_id: str, ctx: Context = None) -> dict:
        """Mark a comment as resolved by ID."""
        db_path = ctx.request_context.lifespan_context.db_path
        conn = init_db(db_path)
        try:
            user = _get_user_from_ctx(ctx)
            if not user:
                return {"error": "Unauthorized"}
            store = CommentStorage(conn)
            updated = store.update_status(user["id"], comment_id, "resolved")
            if not updated:
                return {"error": "Comment not found", "comment_id": comment_id}
            return updated
        finally:
            conn.close()

    @server.tool()
    def awr_delete_comment(comment_id: str, ctx: Context = None) -> dict:
        """Delete a comment by ID."""
        db_path = ctx.request_context.lifespan_context.db_path
        conn = init_db(db_path)
        try:
            user = _get_user_from_ctx(ctx)
            if not user:
                return {"error": "Unauthorized"}
            store = CommentStorage(conn)
            if not store.delete(user["id"], comment_id):
                return {"error": "Comment not found", "comment_id": comment_id}
            return {"deleted": True}
        finally:
            conn.close()
