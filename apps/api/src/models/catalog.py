"""B216 (v0.9.10.3): typed responses for /api/catalog/* routes."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CatalogColumn(BaseModel):
    """Column metadata from information_schema."""
    model_config = ConfigDict(extra="allow")

    name: str
    data_type: str
    nullable: Optional[bool] = None
    default: Optional[str] = None


class CatalogTable(BaseModel):
    """A single discovered table — output of `catalog.Table.to_dict()`."""
    model_config = ConfigDict(extra="allow")

    name: str
    plugin_id: str
    table_type: Optional[str] = Field(default=None, description="'BASE TABLE' | 'VIEW'.")
    row_count_estimate: Optional[int] = None
    columns: list[CatalogColumn] = Field(
        default_factory=list,
        description="Column metadata from information_schema, ordered by ordinal_position.",
    )


class CatalogPluginGroup(BaseModel):
    """All discovered tables for one plugin — used by /catalog/tables."""
    id: str = Field(..., description="Plugin slug.")
    tables: list[CatalogTable]


class CatalogTablesGroupedResponse(BaseModel):
    """GET /api/catalog/tables — every plugin's tables, grouped."""
    plugins: list[CatalogPluginGroup]


class CatalogPluginTablesResponse(BaseModel):
    """GET /api/catalog/plugins/{plugin_id}/tables.

    Returns empty `tables` (not 404) when the plugin has no discovered
    tables, so the frontend can render an empty state.
    """
    plugin_id: str
    tables: list[CatalogTable]
    manifest_drift: Any = Field(
        default=None,
        description="Output of catalog.detect_manifest_drift — shape varies, may be null.",
    )


class CatalogTableRowsResponse(BaseModel):
    """GET /api/catalog/plugins/{plugin_id}/tables/{table_name}/rows."""
    rows: list[dict[str, Any]]
    total: int
    page: int
    limit: int
