"""
Datasets API — upload CSV files, store as JSONB, query and embed in CMS pages.
Each dataset has its own column structure. No shared schema required.
"""
import csv
import io
import json
import re
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile

from ..db import get_pg_conn, dict_cursor
from ..rbac import requires, register_route
from ..models import ErrorDetail, RBACErrorDetail
from ..models.datasets import (
    DatasetDeleteResponse,
    DatasetDetailResponse,
    DatasetUploadResponse,
    DatasetsListResponse,
)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

# B228: register datasets routes.
register_route("POST", "/api/datasets/upload", "datasets.write")
register_route("GET", "/api/datasets", "datasets.read")
register_route("GET", "/api/datasets/{slug}", "datasets.read")
register_route("DELETE", "/api/datasets/{slug}", "system.admin")


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _infer_type(values: list) -> str:
    """Infer column type from sample values."""
    nums = 0
    for v in values[:50]:
        if v is None or v == "":
            continue
        try:
            float(str(v).replace(",", "").replace("$", "").replace("%", ""))
            nums += 1
        except ValueError:
            pass
    return "number" if nums > len(values) * 0.6 else "string"


def _parse_csv(content: str) -> dict:
    """Parse CSV string → {columns, column_types, data, row_count}."""
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        return {"columns": [], "column_types": {}, "data": [], "row_count": 0}

    columns = [c.strip() for c in rows[0]]
    data = []
    for row in rows[1:]:
        if len(row) == 0 or all(c.strip() == "" for c in row):
            continue
        # Pad or trim to match column count
        padded = row[:len(columns)] + [""] * max(0, len(columns) - len(row))
        data.append(padded)

    # Infer types per column
    column_types = {}
    for i, col in enumerate(columns):
        sample = [row[i] for row in data[:100] if i < len(row)]
        column_types[col] = _infer_type(sample)

    return {
        "columns": columns,
        "column_types": column_types,
        "data": data,
        "row_count": len(data),
    }


# ── Upload CSV ────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    operation_id="datasets.upload",
    response_model=DatasetUploadResponse,
    response_model_exclude_none=True,
    summary="Upload a CSV dataset (multipart form)",
    responses={
        400: {"model": ErrorDetail, "description": "Missing/invalid file or empty CSV."},
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the datasets.write permission."},
    },
)
async def upload_dataset(
    request: Request,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    _: None = Depends(requires("datasets.write")),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files are supported")

    content = (await file.read()).decode("utf-8-sig")  # Handle BOM
    file_size = len(content.encode("utf-8"))

    parsed = _parse_csv(content)
    if parsed["row_count"] == 0:
        raise HTTPException(400, "CSV file is empty or could not be parsed")

    ds_name = name or file.filename.rsplit(".", 1)[0]
    ds_slug = slug or _slugify(ds_name)
    ds_tags = [t.strip() for t in (tags or "").split(",") if t.strip()]

    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            INSERT INTO datasets (name, slug, description, columns, column_types, data, row_count, file_size, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                columns = EXCLUDED.columns,
                column_types = EXCLUDED.column_types,
                data = EXCLUDED.data,
                row_count = EXCLUDED.row_count,
                file_size = EXCLUDED.file_size,
                tags = EXCLUDED.tags,
                updated_at = now()
            RETURNING id, name, slug, row_count, file_size, columns, column_types, uploaded_at, updated_at
        """, (
            ds_name, ds_slug, description,
            json.dumps(parsed["columns"]),
            json.dumps(parsed["column_types"]),
            json.dumps(parsed["data"]),
            parsed["row_count"], file_size, ds_tags,
        ))
        row = cur.fetchone()

    for k in ("uploaded_at", "updated_at"):
        if row.get(k) and hasattr(row[k], "isoformat"):
            row[k] = row[k].isoformat()

    return row


# ── List all datasets ─────────────────────────────────────────────────────

@router.get(
    "",
    operation_id="datasets.list",
    response_model=DatasetsListResponse,
    response_model_exclude_none=True,
    summary="List dataset metadata (no data blob)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the datasets.read permission."},
    },
)
def list_datasets(_: None = Depends(requires("datasets.read"))):
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT id, name, slug, description, columns, column_types,
                   row_count, file_size, tags, uploaded_at, updated_at
            FROM datasets
            ORDER BY updated_at DESC
        """)
        rows = cur.fetchall()

    for r in rows:
        for k in ("uploaded_at", "updated_at"):
            if r.get(k) and hasattr(r[k], "isoformat"):
                r[k] = r[k].isoformat()

    return {"datasets": rows, "count": len(rows)}


# ── Get dataset by slug (with data) ──────────────────────────────────────

@router.get(
    "/{slug}",
    operation_id="datasets.detail",
    response_model=DatasetDetailResponse,
    response_model_exclude_none=True,
    summary="Get a dataset including its data matrix (sortable, paginated)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the datasets.read permission."},
        404: {"model": ErrorDetail, "description": "Dataset not found."},
    },
)
def get_dataset(
    slug: str,
    limit: int = Query(0, ge=0, description="Limit rows (0 = all)"),
    offset: int = Query(0, ge=0),
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc"),
    _: None = Depends(requires("datasets.read")),
):
    with get_pg_conn() as conn:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM datasets WHERE slug = %s", (slug,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(404, "Dataset not found")

    for k in ("uploaded_at", "updated_at"):
        if row.get(k) and hasattr(row[k], "isoformat"):
            row[k] = row[k].isoformat()

    data = row["data"]
    columns = row["columns"]

    # Sort
    if sort_by and sort_by in columns:
        col_idx = columns.index(sort_by)
        col_type = row["column_types"].get(sort_by, "string")
        reverse = sort_order == "desc"

        def sort_key(r):
            v = r[col_idx] if col_idx < len(r) else ""
            if col_type == "number":
                try:
                    return float(str(v).replace(",", "").replace("$", "").replace("%", ""))
                except (ValueError, TypeError):
                    return 0
            return str(v).lower()

        data = sorted(data, key=sort_key, reverse=reverse)

    # Paginate
    total = len(data)
    if offset > 0:
        data = data[offset:]
    if limit > 0:
        data = data[:limit]

    row["data"] = data
    row["total_rows"] = total
    row["data_as_of"] = row["updated_at"]

    return row


# ── Delete dataset ────────────────────────────────────────────────────────

@router.delete(
    "/{slug}",
    operation_id="datasets.delete",
    response_model=DatasetDeleteResponse,
    summary="Delete a dataset (admin only)",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        403: {"model": RBACErrorDetail, "description": "Caller lacks the system.admin permission."},
        404: {"model": ErrorDetail, "description": "Dataset not found."},
    },
)
def delete_dataset(
    slug: str,
    request: Request,
    _: None = Depends(requires("system.admin")),
):
    with get_pg_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM datasets WHERE slug = %s RETURNING slug", (slug,))
        deleted = cur.fetchone()
    if not deleted:
        raise HTTPException(404, "Dataset not found")
    return {"deleted": slug}
