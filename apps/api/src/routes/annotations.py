"""
/api/annotations — Annotation CRUD with semantic layer and undo support.

Annotations add contextual meaning to data: algorithm updates, outages,
campaign changes, analyst notes.

Storage: Postgres (annotations + annotation_history tables).
Semantic: meaning, impact_scope, semantic_score (useful|neutral|useless), semantic_note.
Undo: every change is snapshotted in annotation_history — restore any previous state.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ..db import get_pg_conn, rows_as_dicts
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.annotations import (
    AnnotationDeleteResponse,
    AnnotationHistoryResponse,
    AnnotationRow,
    AnnotationScoreResponse,
    AnnotationUndoResponse,
    AnnotationsListResponse,
)

logger = logging.getLogger("nousviz.api.annotations")
router = APIRouter(tags=["annotations"])

# B228: register annotations routes.
register_route("GET", "/api/annotations", "annotations.read")
register_route("POST", "/api/annotations", "annotations.write")
register_route("GET", "/api/annotations/{annotation_id}", "annotations.read")
register_route("PUT", "/api/annotations/{annotation_id}", "annotations.write")
register_route("DELETE", "/api/annotations/{annotation_id}", "annotations.write")
register_route("GET", "/api/annotations/{annotation_id}/history", "annotations.read")
register_route("POST", "/api/annotations/{annotation_id}/undo", "annotations.write")
register_route("POST", "/api/annotations/{annotation_id}/score", "annotations.write")


# ── Models ────────────────────────────────────────────────────────────────

class AnnotationCreate(BaseModel):
    title: str
    description: Optional[str] = None
    source: str = "manual"
    category: str = "note"
    severity: str = "info"
    color: Optional[str] = None
    plugin_id: Optional[str] = None
    dataset: Optional[str] = None
    date_start: str
    date_end: Optional[str] = None
    scope_filters: dict = {}
    tags: list[str] = []
    pinned: bool = False
    # Semantic fields
    semantic_meaning: Optional[str] = None
    impact_scope: list[str] = []
    semantic_score: Optional[str] = None   # useful | neutral | useless
    semantic_note: Optional[str] = None


class AnnotationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    color: Optional[str] = None
    plugin_id: Optional[str] = None
    dataset: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    scope_filters: Optional[dict] = None
    tags: Optional[list[str]] = None
    pinned: Optional[bool] = None
    archived: Optional[bool] = None
    # Semantic fields
    semantic_meaning: Optional[str] = None
    impact_scope: Optional[list[str]] = None
    semantic_score: Optional[str] = None
    semantic_note: Optional[str] = None


def _snapshot(cur, annotation_id: str) -> Optional[dict]:
    """Fetch current row as a dict for history snapshotting."""
    cur.execute("SELECT * FROM annotations WHERE id = %s", (annotation_id,))
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    data = dict(zip(cols, row))
    # Convert non-JSON-serialisable types
    for k, v in data.items():
        if hasattr(v, "isoformat"):
            data[k] = v.isoformat()
    return data


def _write_history(cur, annotation_id: str, action: str, snapshot: Optional[dict]) -> None:
    cur.execute("""
        INSERT INTO annotation_history (annotation_id, action, snapshot)
        VALUES (%s, %s, %s)
    """, (annotation_id, action, json.dumps(snapshot or {})))


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get(
    "/annotations",
    operation_id="annotations.list",
    response_model=AnnotationsListResponse,
    response_model_exclude_none=True,
    summary="List annotations (pinned-first; rich filter set)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the annotations.read permission."},
    },
)
def list_annotations(
    plugin_id: Optional[str] = None,
    dataset: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    semantic_score: Optional[str] = None,
    pinned: Optional[bool] = None,
    include_archived: bool = False,
    limit: int = Query(200, le=1000),
    _: None = Depends(requires("annotations.read")),
):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        sql = "SELECT * FROM annotations WHERE 1=1"
        params: list = []

        if not include_archived:
            sql += " AND archived = FALSE"
        if pinned is not None:
            sql += " AND pinned = %s"
            params.append(pinned)
        if plugin_id:
            sql += " AND plugin_id = %s"
            params.append(plugin_id)
        if dataset:
            sql += " AND dataset = %s"
            params.append(dataset)
        if category:
            sql += " AND category = %s"
            params.append(category)
        if semantic_score:
            sql += " AND semantic_score = %s"
            params.append(semantic_score)
        if date_from:
            sql += " AND (date_end IS NULL OR date_end >= %s)"
            params.append(date_from)
        if date_to:
            sql += " AND date_start <= %s"
            params.append(date_to)

        sql += " ORDER BY pinned DESC, date_start DESC LIMIT %s"
        params.append(limit)

        cur.execute(sql, params)
        rows = rows_as_dicts(cur)

    # Serialize dates
    for r in rows:
        for k in ("date_start", "date_end", "created_at", "updated_at"):
            if r.get(k) and hasattr(r[k], "isoformat"):
                r[k] = r[k].isoformat()

    return {"annotations": rows, "count": len(rows)}


@router.post(
    "/annotations",
    operation_id="annotations.create",
    response_model=AnnotationRow,
    response_model_exclude_none=True,
    summary="Create an annotation (writes a 'created' history snapshot)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the annotations.write permission."},
    },
)
def create_annotation(
    req: AnnotationCreate,
    request: Request,
    _: None = Depends(requires("annotations.write")),
):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO annotations (
                title, description, source, category, severity, color,
                plugin_id, dataset, date_start, date_end,
                scope_filters, tags, pinned,
                semantic_meaning, impact_scope, semantic_score, semantic_note
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING *
        """, (
            req.title, req.description, req.source, req.category, req.severity, req.color,
            req.plugin_id, req.dataset, req.date_start, req.date_end,
            json.dumps(req.scope_filters), req.tags, req.pinned,
            req.semantic_meaning, req.impact_scope, req.semantic_score, req.semantic_note,
        ))
        row = dict(zip([d[0] for d in cur.description], cur.fetchone()))
        _write_history(cur, str(row["id"]), "created", None)

    logger.info(f"Annotation created: {req.title}")
    return _serialize(row)


@router.get(
    "/annotations/{annotation_id}",
    operation_id="annotations.detail",
    response_model=AnnotationRow,
    response_model_exclude_none=True,
    summary="Get a single annotation",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the annotations.read permission."},
        404: {"model": ErrorDetail, "description": "Annotation not found."},
    },
)
def get_annotation(annotation_id: str, _: None = Depends(requires("annotations.read"))):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM annotations WHERE id = %s", (annotation_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Annotation not found")
        return _serialize(dict(zip([d[0] for d in cur.description], row)))


@router.put(
    "/annotations/{annotation_id}",
    operation_id="annotations.update",
    response_model=AnnotationRow,
    response_model_exclude_none=True,
    summary="Update an annotation (writes an 'updated' history snapshot)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the annotations.write permission."},
        404: {"model": ErrorDetail, "description": "Annotation not found."},
    },
)
def update_annotation(
    annotation_id: str,
    req: AnnotationUpdate,
    request: Request,
    _: None = Depends(requires("annotations.write")),
):
    with get_pg_conn() as conn:
        cur = conn.cursor()

        # Snapshot before change
        before = _snapshot(cur, annotation_id)
        if not before:
            raise HTTPException(404, "Annotation not found")
        _write_history(cur, annotation_id, "updated", before)

        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        if not updates:
            return before

        set_clauses = ", ".join(f"{k} = %s" for k in updates)
        values = list(updates.values()) + [annotation_id]
        cur.execute(
            f"UPDATE annotations SET {set_clauses}, updated_at = now() WHERE id = %s RETURNING *",
            values
        )
        row = dict(zip([d[0] for d in cur.description], cur.fetchone()))

    logger.info(f"Annotation updated: {annotation_id}")
    return _serialize(row)


@router.delete(
    "/annotations/{annotation_id}",
    operation_id="annotations.delete",
    response_model=AnnotationDeleteResponse,
    summary="Delete an annotation (soft by default; permanent=true to hard-delete)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the annotations.write permission."},
        404: {"model": ErrorDetail, "description": "Annotation not found."},
    },
)
def delete_annotation(
    annotation_id: str,
    request: Request,
    permanent: bool = False,
    _: None = Depends(requires("annotations.write")),
):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        before = _snapshot(cur, annotation_id)
        if not before:
            raise HTTPException(404, "Annotation not found")
        _write_history(cur, annotation_id, "deleted", before)
        if permanent:
            cur.execute("DELETE FROM annotations WHERE id = %s", (annotation_id,))
        else:
            # Soft delete — moves to archive
            cur.execute(
                "UPDATE annotations SET archived = TRUE, updated_at = now() WHERE id = %s",
                (annotation_id,)
            )

    logger.info(f"Annotation {'permanently deleted' if permanent else 'archived (soft delete)'}: {annotation_id}")
    return {"status": "deleted", "permanent": permanent}


# ── Undo ─────────────────────────────────────────────────────────────────

@router.get(
    "/annotations/{annotation_id}/history",
    operation_id="annotations.history",
    response_model=AnnotationHistoryResponse,
    response_model_exclude_none=True,
    summary="Full change history for an annotation (newest-first)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the annotations.read permission."},
    },
)
def get_annotation_history(
    annotation_id: str,
    _: None = Depends(requires("annotations.read")),
):
    """Show the full change history for an annotation."""
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, action, changed_by, changed_at, snapshot
            FROM annotation_history
            WHERE annotation_id = %s
            ORDER BY changed_at DESC
        """, (annotation_id,))
        rows = rows_as_dicts(cur)
    for r in rows:
        if r.get("changed_at"):
            r["changed_at"] = r["changed_at"].isoformat()
    return {"history": rows, "count": len(rows)}


@router.post(
    "/annotations/{annotation_id}/undo",
    operation_id="annotations.undo",
    response_model=AnnotationUndoResponse,
    response_model_exclude_none=True,
    summary="Restore the annotation to its previous state",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the annotations.write permission."},
        404: {"model": ErrorDetail, "description": "No undoable history."},
    },
)
def undo_annotation(
    annotation_id: str,
    request: Request,
    _: None = Depends(requires("annotations.write")),
):
    """Restore the annotation to its state before the last change.

    Two outcomes: undoing a 'created' action archives the annotation
    (since there's nothing to restore to); undoing an 'updated' action
    restores the previous snapshot and removes that history entry.
    """
    with get_pg_conn() as conn:
        cur = conn.cursor()

        # Get the most recent history entry that has a snapshot to restore
        cur.execute("""
            SELECT id, action, snapshot FROM annotation_history
            WHERE annotation_id = %s AND action IN ('created', 'updated')
            ORDER BY changed_at DESC
            LIMIT 1
        """, (annotation_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "No history to undo")

        history_id, action, snapshot = row

        if action == "created":
            # Undo a create = soft delete
            cur.execute(
                "UPDATE annotations SET archived = TRUE, updated_at = now() WHERE id = %s",
                (annotation_id,)
            )
            _write_history(cur, annotation_id, "restored", snapshot)
            return {"status": "undone", "action": "archived (creation undone)"}

        # Undo an update = restore snapshot
        s = snapshot
        cur.execute("""
            UPDATE annotations SET
                title = %s, description = %s, category = %s, severity = %s,
                color = %s, plugin_id = %s, dataset = %s,
                date_start = %s, date_end = %s, scope_filters = %s,
                tags = %s, pinned = %s, archived = %s,
                semantic_meaning = %s, impact_scope = %s,
                semantic_score = %s, semantic_note = %s,
                updated_at = now()
            WHERE id = %s
        """, (
            s.get("title"), s.get("description"), s.get("category"), s.get("severity"),
            s.get("color"), s.get("plugin_id"), s.get("dataset"),
            s.get("date_start"), s.get("date_end"),
            json.dumps(s.get("scope_filters", {})),
            s.get("tags", []), s.get("pinned", False), s.get("archived", False),
            s.get("semantic_meaning"), s.get("impact_scope", []),
            s.get("semantic_score"), s.get("semantic_note"),
            annotation_id,
        ))
        # Remove the history entry we just undid
        cur.execute("DELETE FROM annotation_history WHERE id = %s", (history_id,))
        _write_history(cur, annotation_id, "restored", s)

    return {"status": "undone", "restored_to": snapshot}


# ── Semantic score endpoint (quick score without full update) ─────────────

@router.post(
    "/annotations/{annotation_id}/score",
    operation_id="annotations.score",
    response_model=AnnotationScoreResponse,
    summary="Quick semantic score (useful | neutral | useless)",
    responses={
        400: {"model": ErrorDetail, "description": "Invalid score value."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the annotations.write permission."},
        404: {"model": ErrorDetail, "description": "Annotation not found."},
    },
)
def score_annotation(
    annotation_id: str,
    request: Request,
    score: str,
    note: Optional[str] = None,
    _: None = Depends(requires("annotations.write")),
):
    """Quick-score an annotation as useful / neutral / useless."""
    if score not in ("useful", "neutral", "useless"):
        raise HTTPException(400, "score must be useful | neutral | useless")
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE annotations SET semantic_score = %s, semantic_note = %s, updated_at = now()
            WHERE id = %s
        """, (score, note, annotation_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Annotation not found")
    return {"status": "scored", "score": score}


# ── Helper ────────────────────────────────────────────────────────────────

def _serialize(row: dict) -> dict:
    for k in ("date_start", "date_end", "created_at", "updated_at"):
        if row.get(k) and hasattr(row[k], "isoformat"):
            row[k] = row[k].isoformat()
    return row
