from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user
from app.models import CommentCreate
from app.storage.comments import CommentStorage

router = APIRouter(prefix="/api/comments", tags=["comments"])

MAX_COMMENT_LENGTH = 10_000


def _get_comment_storage() -> CommentStorage:
    from app.main import get_comment_storage
    return get_comment_storage()


@router.get("")
def list_comments(
    page_url: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
    store: CommentStorage = Depends(_get_comment_storage),
):
    return store.get_all(user["id"], page_url=page_url, status=status)


@router.post("", status_code=201)
def create_comment(
    body: CommentCreate,
    user: dict = Depends(get_current_user),
    store: CommentStorage = Depends(_get_comment_storage),
):
    if len(body.comment_text) > MAX_COMMENT_LENGTH:
        raise HTTPException(status_code=400, detail=f"comment_text too long (max {MAX_COMMENT_LENGTH} chars)")
    return store.create(user["id"], body)


@router.delete("")
def delete_all_comments(
    page_url: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
    store: CommentStorage = Depends(_get_comment_storage),
):
    if not page_url and not status:
        raise HTTPException(status_code=400, detail="page_url or status query parameter required for DELETE")
    removed = store.delete_all(user["id"], page_url=page_url, status=status)
    return {"deleted": removed}


@router.delete("/{comment_id}")
def delete_comment(
    comment_id: str,
    user: dict = Depends(get_current_user),
    store: CommentStorage = Depends(_get_comment_storage),
):
    if not store.delete(user["id"], comment_id):
        raise HTTPException(status_code=404, detail=f"comment {comment_id} not found")
    from fastapi.responses import Response
    return Response(status_code=204)


@router.patch("/{comment_id}")
def patch_comment(
    comment_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
    store: CommentStorage = Depends(_get_comment_storage),
):
    new_status = body.get("status")
    if new_status != "resolved":
        raise HTTPException(status_code=400, detail='invalid status value, only "resolved" is accepted')
    updated = store.update_status(user["id"], comment_id, new_status)
    if not updated:
        raise HTTPException(status_code=404, detail=f"comment {comment_id} not found")
    return updated
