from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class Course(BaseModel):
    courseId: str
    title: str
    available: str
    lastAccessed: str | None = None


class ContentItem(BaseModel):
    id: str
    title: str
    contentHandlerId: str | None = None
    hasChildren: bool = False
    description: str | None = None
    modified: str | None = None


class ContentItemWithPath(ContentItem):
    breadcrumb: list[str] = []


class Announcement(BaseModel):
    id: str
    title: str
    body: str | None = None
    created: str | None = None
    modified: str | None = None
    available: bool | None = None


class GradebookColumn(BaseModel):
    id: str
    name: str
    displayName: str | None = None
    score: dict[str, Any] | None = None
    available: bool | None = None
    contentId: str | None = None


class DownloadInfo(BaseModel):
    url: str
    filename: str | None = None
    contentId: str


class DownloadResult(BaseModel):
    localPath: str
    filename: str
    contentId: str
