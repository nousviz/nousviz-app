"""B216 (v0.9.10.3): typed responses for /api/data-port/* routes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class DataportTabIndexEntry(BaseModel):
    """Compact tab descriptor used in the dataport plugin index."""
    id: str
    label: str


class DataportPluginIndexEntry(BaseModel):
    """A single plugin in the dataport index — slug + tab labels."""
    slug: str
    tabs: list[DataportTabIndexEntry]


class DataportPluginsListResponse(BaseModel):
    """GET /api/data-port/plugins — installed plugins that ship dataport.yaml."""
    plugins: list[DataportPluginIndexEntry]


class DataportPluginConfigResponse(BaseModel):
    """GET /api/data-port/plugins/{plugin_slug} — full dataport.yaml.

    Schema is plugin-author-defined; we accept it verbatim.
    """
    model_config = ConfigDict(extra="allow")


class DataportTabRowsResponse(BaseModel):
    """GET /api/data-port/plugins/{plugin_slug}/tab/{tab_id}.

    Paginated rows from the tab's declared SQL table. `rows` is a list
    of plugin-table-shaped dicts (column types vary per table), so
    typed as `list[dict[str, Any]]` rather than a fixed shape.
    """
    rows: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
