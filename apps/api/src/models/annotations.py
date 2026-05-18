"""B216 (v0.9.10.3): typed responses for /api/annotations/* routes."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class AnnotationRow(BaseModel):
    """A single annotations row.

    The annotation schema has many optional/JSONB fields; extra='allow'
    keeps the model honest as new columns land (semantic_*, impact_scope,
    etc. were added across v0.8/v0.9).
    """
    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    description: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    color: Optional[str] = None
    plugin_id: Optional[str] = None
    dataset: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    scope_filters: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    pinned: Optional[bool] = None
    archived: Optional[bool] = None
    semantic_meaning: Optional[str] = None
    impact_scope: Optional[list[str]] = None
    semantic_score: Optional[str] = Field(
        default=None,
        description="'useful' | 'neutral' | 'useless'.",
    )
    semantic_note: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AnnotationsListResponse(BaseModel):
    """GET /api/annotations — pinned-first ordering, rich filter set."""
    annotations: list[AnnotationRow]
    count: int


class AnnotationDeleteResponse(BaseModel):
    """DELETE /api/annotations/{annotation_id}.

    `permanent=true` actually deletes; default is soft-delete (archived=true).
    """
    status: str = Field(default="deleted", description="Always 'deleted' (soft or hard).")
    permanent: bool


class AnnotationHistoryEntry(BaseModel):
    """A single annotation_history row — one change to an annotation."""
    model_config = ConfigDict(extra="allow")

    id: str
    action: str = Field(..., description="'created' | 'updated' | 'deleted' | 'restored'.")
    changed_by: Optional[str] = None
    changed_at: Optional[str] = None
    snapshot: Optional[dict[str, Any]] = Field(
        default=None,
        description="Annotation state before the change (or after, for 'created').",
    )


class AnnotationHistoryResponse(BaseModel):
    """GET /api/annotations/{annotation_id}/history."""
    history: list[AnnotationHistoryEntry]
    count: int


class AnnotationUndoResponse(BaseModel):
    """POST /api/annotations/{annotation_id}/undo.

    Two shapes depending on what was undone:
    - Undoing a 'created' action: `action='archived (creation undone)'`,
      no `restored_to`.
    - Undoing an 'updated' action: `restored_to` carries the snapshot.
    """
    model_config = ConfigDict(extra="allow")

    status: str = Field(default="undone", description="Always 'undone' on success.")
    action: Optional[str] = None
    restored_to: Optional[dict[str, Any]] = None


class AnnotationScoreResponse(BaseModel):
    """POST /api/annotations/{annotation_id}/score — quick semantic score."""
    status: str = Field(default="scored", description="Always 'scored' on success.")
    score: str = Field(..., description="'useful' | 'neutral' | 'useless'.")
