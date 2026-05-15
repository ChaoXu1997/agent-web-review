from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel


class CommentCreate(BaseModel):
    page_url: str
    comment_text: str
    element_selector: str = ""
    element_xpath: str = ""
    element_text: str = ""
    element_html: str = ""
    screenshot_b64: str = ""
    area: Optional[dict] = None
    status: str = "open"


class CommentResponse(BaseModel):
    id: str
    user_id: str
    page_url: str
    comment_text: str
    element_selector: str = ""
    element_xpath: str = ""
    element_text: str = ""
    element_html: str = ""
    screenshot_b64: str = ""
    area: Optional[dict] = None
    timestamp: str
    status: str = "open"


class UserResponse(BaseModel):
    id: str
    name: str
    api_key: str
    created_at: str


class CreateUserRequest(BaseModel):
    name: str


class ProjectMappingCreate(BaseModel):
    page_url: str
    project_path: str


class ProjectMappingResponse(BaseModel):
    id: str
    user_id: str
    page_url: str
    project_path: str


def new_id() -> str:
    return uuid4().hex


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
