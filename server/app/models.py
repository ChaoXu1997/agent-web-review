from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

# Size limits for unauthenticated POST payloads (protect server memory).
MAX_SCREENSHOT_B64 = 5_000_000  # ~3.7MB binary base64-encoded
MAX_ELEMENT_FIELD = 50_000


class CommentCreate(BaseModel):
    page_url: str
    comment_text: str
    element_selector: str = ""
    element_xpath: str = ""
    element_text: str = Field(default="", max_length=MAX_ELEMENT_FIELD)
    element_html: str = Field(default="", max_length=MAX_ELEMENT_FIELD)
    screenshot_b64: str = Field(default="", max_length=MAX_SCREENSHOT_B64)
    area: Optional[dict] = None
    status: str = "open"


class CommentResponse(BaseModel):
    id: str
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


class ProjectMappingCreate(BaseModel):
    page_url: str
    project_path: str


class ProjectMappingResponse(BaseModel):
    page_url: str
    project_path: str


def new_id() -> str:
    return uuid4().hex


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
