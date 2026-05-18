"""B216 (v0.9.10.3): typed responses for /api/notes/* routes."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class NoteEntry(BaseModel):
    """A single notes row.

    POST and PUT return the raw row; LIST wraps in a `notes` envelope.
    extra='allow' covers any future columns (e.g. tags) without a model bump.
    """
    model_config = ConfigDict(extra="allow")

    id: str
    page_path: Optional[str] = None
    plugin_id: Optional[str] = None
    body: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    pinned: Optional[bool] = None
    archived: Optional[bool] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class NotesListResponse(BaseModel):
    """GET /api/notes — pinned-first ordering, optional page-path/plugin filter."""
    notes: list[NoteEntry]
    count: int


class NoteDeleteResponse(BaseModel):
    """DELETE /api/notes/{note_id}."""
    status: str = Field(default="deleted", description="Always 'deleted' on success.")
