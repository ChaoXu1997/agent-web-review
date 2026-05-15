from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Header

from app.auth import verify_admin_token
from app.models import CreateUserRequest
from app.storage.users import UserStorage

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_admin_token() -> str:
    from app.main import get_admin_token
    return get_admin_token()


def _get_user_storage() -> UserStorage:
    from app.main import get_user_storage
    return get_user_storage()


def _require_admin(authorization: str = Header(default="")) -> None:
    token = _get_admin_token()
    if not token:
        raise HTTPException(status_code=500, detail="AWR_ADMIN_TOKEN not configured")
    provided = authorization.removeprefix("Bearer ").strip()
    if not verify_admin_token(provided, token):
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.get("/keys")
def list_keys(_: None = Depends(_require_admin)):
    store = _get_user_storage()
    return store.list_all()


@router.post("/keys", status_code=201)
def create_key(
    body: CreateUserRequest,
    _: None = Depends(_require_admin),
):
    store = _get_user_storage()
    return store.create(body.name)


@router.delete("/keys/{user_id}")
def revoke_key(
    user_id: str,
    _: None = Depends(_require_admin),
):
    store = _get_user_storage()
    if not store.delete(user_id):
        raise HTTPException(status_code=404, detail="user not found")
    return {"deleted": True}
