"""
/api/notes — Page notes with time-aware relevance

Notes are attached to specific pages and optionally to date ranges.
They're always visible on the page but styled differently based on
whether the current view's date range overlaps the note's time range.

Storage: Postgres `notes` table (migration 024).
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..db import get_pg_conn, rows_as_dicts
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.notes import NoteDeleteResponse, NoteEntry, NotesListResponse

logger = logging.getLogger("nousviz.api.notes")

router = APIRouter(tags=["notes"])

# B228: register all routes in this file.
register_route("GET", "/api/notes", "notes.read")
register_route("POST", "/api/notes", "notes.write")
register_route("PUT", "/api/notes/{note_id}", "notes.write")
register_route("DELETE", "/api/notes/{note_id}", "notes.write")


class NoteCreate(BaseModel):
    page_path: str
    body: str
    plugin_id: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    pinned: bool = False


class NoteUpdate(BaseModel):
    body: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    pinned: bool | None = None
    resolved: bool | None = None
    archived: bool | None = None


def _serialize(rows: list[dict]) -> list[dict]:
    for r in rows:
        for k in ("date_start", "date_end", "created_at", "updated_at"):
            if r.get(k) and hasattr(r[k], "isoformat"):
                r[k] = r[k].isoformat()
    return rows


@router.get(
    "/notes",
    operation_id="notes.list",
    response_model=NotesListResponse,
    response_model_exclude_none=True,
    summary="List notes (pinned-first, optional page-path/plugin filter)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the notes.read permission."},
    },
)
async def list_notes(
    page_path: str | None = None,
    plugin_id: str | None = None,
    include_archived: bool = False,
    _: None = Depends(requires("notes.read")),
):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        sql = "SELECT * FROM notes WHERE 1=1"
        params: list = []

        if not include_archived:
            sql += " AND archived = false"
        if page_path:
            sql += " AND page_path = %s"
            params.append(page_path)
        if plugin_id:
            sql += " AND plugin_id = %s"
            params.append(plugin_id)

        sql += " ORDER BY pinned DESC, created_at ASC"
        cur.execute(sql, params)
        rows = rows_as_dicts(cur)

    _serialize(rows)
    return {"notes": rows, "count": len(rows)}


@router.post(
    "/notes",
    operation_id="notes.create",
    response_model=NoteEntry,
    response_model_exclude_none=True,
    summary="Create a note attached to a page (and optional date range)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the notes.write permission."},
    },
)
async def create_note(
    req: NoteCreate,
    request: Request,
    _: None = Depends(requires("notes.write")),
):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO notes (page_path, plugin_id, body, date_start, date_end, pinned)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (req.page_path, req.plugin_id, req.body, req.date_start, req.date_end, req.pinned))
        row = rows_as_dicts(cur)[0]

    _serialize([row])
    return row


@router.put(
    "/notes/{note_id}",
    operation_id="notes.update",
    response_model=NoteEntry,
    response_model_exclude_none=True,
    summary="Update a note (partial — null fields skipped)",
    responses={
        400: {"model": ErrorDetail, "description": "Empty body."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the notes.write permission."},
        404: {"model": ErrorDetail, "description": "Note not found."},
    },
)
async def update_note(
    note_id: str,
    req: NoteUpdate,
    request: Request,
    _: None = Depends(requires("notes.write")),
):
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "Nothing to update")

    updates["updated_at"] = datetime.now(timezone.utc)
    set_parts = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [note_id]

    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE notes SET {set_parts} WHERE id = %s RETURNING *",
            values,
        )
        rows = rows_as_dicts(cur)

    if not rows:
        raise HTTPException(404, "Note not found")
    _serialize(rows)
    return rows[0]


@router.delete(
    "/notes/{note_id}",
    operation_id="notes.delete",
    response_model=NoteDeleteResponse,
    summary="Delete a note",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the notes.write permission."},
        404: {"model": ErrorDetail, "description": "Note not found."},
    },
)
async def delete_note(
    note_id: str,
    request: Request,
    _: None = Depends(requires("notes.write")),
):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM notes WHERE id = %s RETURNING id", (note_id,))
        deleted = cur.fetchone()

    if not deleted:
        raise HTTPException(404, "Note not found")
    return {"status": "deleted"}
