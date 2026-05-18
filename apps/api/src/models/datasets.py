"""B216 (v0.9.10.3): typed responses for /api/datasets/* routes."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class DatasetSummary(BaseModel):
    """A single datasets row in the list response — metadata only, no `data` blob."""
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    columns: list[str] = Field(
        default_factory=list,
        description="Column names in the order they appeared in the source CSV.",
    )
    column_types: dict[str, str] = Field(
        default_factory=dict,
        description="Inferred type per column ('number' | 'string' | etc.) — used for sort + render hints.",
    )
    row_count: int = 0
    file_size: Optional[int] = Field(default=None, description="Total stored size in bytes.")
    tags: list[str] = Field(default_factory=list, description="Operator-assigned labels.")
    uploaded_at: Optional[str] = None
    updated_at: Optional[str] = None


class DatasetsListResponse(BaseModel):
    """GET /api/datasets — metadata for every dataset, newest-first."""
    datasets: list[DatasetSummary]
    count: int


class DatasetDetailResponse(BaseModel):
    """GET /api/datasets/{slug} — full dataset including the `data` blob.

    Sort + paginate happens server-side; `total_rows` is the unpaginated
    count, `data` carries the (possibly sliced) row matrix.
    """
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    slug: str
    description: Optional[str] = None
    columns: list[str]
    column_types: dict[str, str]
    data: list[list[Any]] = Field(
        ...,
        description="Row-major matrix; inner list values match `columns` ordering.",
    )
    row_count: int
    total_rows: int
    file_size: Optional[int] = None
    tags: list[str] = Field(default_factory=list, description="Operator-assigned labels.")
    uploaded_at: Optional[str] = None
    updated_at: Optional[str] = None
    data_as_of: Optional[str] = None


class DatasetUploadResponse(BaseModel):
    """POST /api/datasets/upload — newly stored dataset row.

    Same shape as DatasetSummary plus the `id` returned by the
    upsert.
    """
    id: str
    name: str
    slug: str
    row_count: int
    file_size: int
    columns: list[str]
    column_types: dict[str, str]
    uploaded_at: Optional[str] = None
    updated_at: Optional[str] = None


class DatasetDeleteResponse(BaseModel):
    """DELETE /api/datasets/{slug}."""
    deleted: str = Field(..., description="Slug of the deleted dataset.")
