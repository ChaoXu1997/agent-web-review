from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.models import ProjectMappingCreate
from app.storage.projects import ProjectMappingStorage

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _get_project_storage() -> ProjectMappingStorage:
    from app.main import get_project_storage

    return get_project_storage()


@router.get("")
def list_projects(
    store: ProjectMappingStorage = Depends(_get_project_storage),
):
    return store.get_all()


@router.post("", status_code=201)
def create_project(
    body: ProjectMappingCreate,
    store: ProjectMappingStorage = Depends(_get_project_storage),
):
    try:
        return store.create(body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("")
def delete_project(
    page_url: str,
    store: ProjectMappingStorage = Depends(_get_project_storage),
):
    if not store.delete(page_url):
        raise HTTPException(status_code=404, detail=f"mapping for {page_url} not found")
    return {"deleted": True}
