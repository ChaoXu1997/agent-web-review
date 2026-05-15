from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.models import ProjectMappingCreate
from app.storage.projects import ProjectMappingStorage

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _get_project_storage() -> ProjectMappingStorage:
    from app.main import get_project_storage
    return get_project_storage()


@router.get("")
def list_projects(
    user: dict = Depends(get_current_user),
    store: ProjectMappingStorage = Depends(_get_project_storage),
):
    return store.get_all(user["id"])


@router.post("", status_code=201)
def create_project(
    body: ProjectMappingCreate,
    user: dict = Depends(get_current_user),
    store: ProjectMappingStorage = Depends(_get_project_storage),
):
    try:
        return store.create(user["id"], body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("")
def delete_project(
    page_url: str,
    user: dict = Depends(get_current_user),
    store: ProjectMappingStorage = Depends(_get_project_storage),
):
    if not store.delete(user["id"], page_url):
        raise HTTPException(status_code=404, detail=f"mapping for {page_url} not found")
    return {"deleted": True}
