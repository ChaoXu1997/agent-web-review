from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.models import CommentCreate
from app.storage.comments import CommentStorage

router = APIRouter(prefix="/api/comments", tags=["comments"])

MAX_COMMENT_LENGTH = 10_000


class CommentStatusUpdate(BaseModel):
    status: Literal["resolved"]


def _get_comment_storage() -> CommentStorage:
    from app.main import get_comment_storage

    return get_comment_storage()


@router.get("")
def list_comments(
    page_url: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    store: CommentStorage = Depends(_get_comment_storage),
):
    return store.get_all(page_url=page_url, status=status)


@router.post("", status_code=201)
def create_comment(
    body: CommentCreate,
    store: CommentStorage = Depends(_get_comment_storage),
):
    if len(body.comment_text) > MAX_COMMENT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"comment_text too long (max {MAX_COMMENT_LENGTH} chars)",
        )
    return store.create(body)


@router.delete("")
def delete_all_comments(
    page_url: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    store: CommentStorage = Depends(_get_comment_storage),
):
    if not page_url and not status:
        raise HTTPException(
            status_code=400,
            detail="page_url or status query parameter required for DELETE",
        )
    removed = store.delete_all(page_url=page_url, status=status)
    return {"deleted": removed}


@router.delete("/{comment_id}")
def delete_comment(
    comment_id: str,
    store: CommentStorage = Depends(_get_comment_storage),
):
    if not store.delete(comment_id):
        raise HTTPException(status_code=404, detail=f"comment {comment_id} not found")
    from fastapi.responses import Response

    return Response(status_code=204)


@router.patch("/{comment_id}")
def patch_comment(
    comment_id: str,
    body: CommentStatusUpdate,
    store: CommentStorage = Depends(_get_comment_storage),
):
    updated = store.update_status(comment_id, body.status)
    if not updated:
        raise HTTPException(status_code=404, detail=f"comment {comment_id} not found")
    from app.routes.sse import sse_manager

    sse_manager.broadcast("comment_resolved", updated)
    return updated
