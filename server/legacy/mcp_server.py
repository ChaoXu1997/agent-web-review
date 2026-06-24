"""MCP Server for Agent Web Review — exposes awr_get_comments tool via stdio."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from storage import CommentStorage
    from project_storage import ProjectMappingStorage


def awr_get_comments(
    storage: "CommentStorage",
    page_url: Optional[str] = None,
    status: Optional[str] = None,
    project_path: Optional[str] = None,
    project_storage: Optional["ProjectMappingStorage"] = None,
) -> list[dict]:
    """Get all comments, optionally filtered by page_url, status, and/or project_path.

    Args:
        storage: CommentStorage instance.
        page_url: Only return comments for this page URL.
        status: Only return comments with this status (e.g. "open", "resolved").
        project_path: Only return comments for URLs mapped to this project path.
        project_storage: ProjectMappingStorage instance (required when project_path is used).
    """
    if project_path is not None:
        if project_storage is None:
            return []
        urls = project_storage.get_urls_by_project_path(project_path)
        if not urls:
            return []
        url_set = set(urls)
        comments = storage.get_all(status=status)
        comments = [c for c in comments if c.page_url in url_set]
        if page_url is not None:
            comments = [c for c in comments if c.page_url == page_url]
    else:
        comments = storage.get_all(page_url=page_url, status=status)
    return [c.to_dict() for c in comments]


def awr_resolve_comment(
    storage: "CommentStorage",
    comment_id: str,
) -> dict:
    """Mark a comment as resolved.

    Args:
        storage: CommentStorage instance.
        comment_id: The ID of the comment to resolve.

    Returns:
        Updated comment dict with status='resolved'.
    """
    updated = storage.update_status(comment_id, "resolved")
    if updated is None:
        return {"error": "Comment not found", "comment_id": comment_id}
    return updated.to_dict()


def awr_delete_comment(
    storage: "CommentStorage",
    comment_id: str,
) -> dict:
    """Delete a comment.

    Args:
        storage: CommentStorage instance.
        comment_id: The ID of the comment to delete.

    Returns:
        {"deleted": True} on success, or {"error": "Comment not found", "comment_id": "..."}.
    """
    ok = storage.delete(comment_id)
    if not ok:
        return {"error": "Comment not found", "comment_id": comment_id}
    return {"deleted": True}


def create_mcp_server(
    storage: "CommentStorage",
    project_storage: Optional["ProjectMappingStorage"] = None,
) -> FastMCP:
    """Create and return a FastMCP server wired to the given CommentStorage."""
    app = FastMCP("agent-web-review")

    @app.tool()
    def _awr_get_comments(
        page_url: Optional[str] = None,
        status: Optional[str] = None,
        project_path: Optional[str] = None,
    ) -> list[dict]:
        """Get all comments, optionally filtered by page_url, status, and/or project_path.

        Args:
            page_url: Only return comments for this page URL.
            status: Only return comments with this status (e.g. "open", "resolved").
            project_path: Only return comments for URLs mapped to this project path.
        """
        return awr_get_comments(
            storage,
            page_url=page_url,
            status=status,
            project_path=project_path,
            project_storage=project_storage,
        )

    @app.tool()
    def _awr_resolve_comment(comment_id: str) -> dict:
        """Mark a comment as resolved.

        Args:
            comment_id: The ID of the comment to resolve.
        """
        return awr_resolve_comment(storage, comment_id=comment_id)

    @app.tool()
    def _awr_delete_comment(comment_id: str) -> dict:
        """Delete a comment.

        Args:
            comment_id: The ID of the comment to delete.
        """
        return awr_delete_comment(storage, comment_id=comment_id)

    return app


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv
    from storage import CommentStorage

    load_dotenv()

    data_dir = os.environ.get("AWR_DATA_DIR")
    storage = CommentStorage(data_dir=data_dir)
    server = create_mcp_server(storage)
    server.run(transport="stdio")
