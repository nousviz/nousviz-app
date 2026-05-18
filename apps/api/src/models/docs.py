"""B216 (v0.9.10.3): typed responses for /api/docs/* routes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocEntry(BaseModel):
    """Index entry for a documentation page."""
    slug: str = Field(..., description="URL-safe identifier, used as the path segment.")
    title: str
    section: str = Field(..., description="Top-level grouping for the docs sidebar.")
    available: bool = Field(..., description="True iff the markdown file exists on disk.")


class DocsListResponse(BaseModel):
    """GET /api/docs — index of all documentation pages."""
    docs: list[DocEntry]


class DocResponse(BaseModel):
    """GET /api/docs/{slug} — full doc page content."""
    slug: str
    title: str
    section: str
    content: str = Field(..., description="Markdown body, UTF-8.")
