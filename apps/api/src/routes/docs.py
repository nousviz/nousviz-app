"""
/api/docs — Serve markdown documentation files from the docs/ directory.

Allowlist-only — no path traversal possible.
"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException

from ..rbac import requires, register_route
from ..models import ErrorDetail
from ..models.docs import DocResponse, DocsListResponse

router = APIRouter(tags=["docs"])

# B228: register docs routes (silent-leak fix). users.read_self because
# docs are not sensitive — any authenticated user can read.
register_route("GET", "/api/docs", "users.read_self")
register_route("GET", "/api/docs/{slug}", "users.read_self")

REPO_ROOT = Path(__file__).resolve().parents[4]

# Allowlist: (slug, title, path_relative_to_repo_root, section)
DOCS_INDEX = [
    ("glossary",               "Glossary",               "docs/glossary.md",                    "platform"),
    ("getting-started",        "Getting Started",        "docs/startup.md",                    "platform"),
    ("plugin-architecture",    "Plugin Architecture",    "docs/plugin-architecture.md",         "plugins"),
    ("plugin-ux-standards",    "Plugin UX Standards",    "docs/plugin-ux-standards.md",         "plugins"),
    ("contributing-a-plugin",  "Contributing a Plugin",  "docs/contributing-a-plugin.md",       "plugins"),
    ("sdk-reference",          "SDK Reference",          "docs/sdk-reference.md",               "plugins"),
    ("client-sdk",             "Client SDK",             "docs/client-sdk.md",                  "platform"),
    ("private-plugins",        "Private Plugins",        "docs/private-plugins.md",             "plugins"),
    ("developer-guide",        "Developer Guide",        "docs/developer-guide.md",             "development"),
    ("security-model",         "Security Model",         "docs/security-model.md",              "platform"),
    ("admin-cli",              "Admin CLI",              "docs/admin-cli.md",                   "platform"),
    ("deploy-workflow",        "Deploy Workflow",        "docs/deploy-workflow.md",             "development"),
    ("design-system",          "Design System",          "docs/design-system.md",               "development"),
    ("contributing",           "Contributing",           "CONTRIBUTING.md",                     "development"),
    ("changelog",              "Changelog",              "CHANGELOG.md",                        "platform"),
]


@router.get(
    "/docs",
    operation_id="docs.list",
    response_model=DocsListResponse,
    summary="Index of available documentation pages",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
    },
)
async def list_docs(_: None = Depends(requires("users.read_self"))):
    """List all available documentation pages.

    Pages are allowlisted in DOCS_INDEX — no filesystem traversal. The
    `available` flag reflects whether the markdown file exists on disk
    so the frontend can grey-out stale entries during dev.
    """
    result = []
    for slug, title, rel_path, section in DOCS_INDEX:
        result.append({
            "slug": slug,
            "title": title,
            "section": section,
            "available": (REPO_ROOT / rel_path).exists(),
        })
    return {"docs": result}


@router.get(
    "/docs/{slug}",
    operation_id="docs.detail",
    response_model=DocResponse,
    summary="Full markdown body of a documentation page",
    responses={
        401: {"model": ErrorDetail, "description": "Missing or invalid session token."},
        404: {"model": ErrorDetail, "description": "Slug not in allowlist or file missing on disk."},
    },
)
async def get_doc(slug: str, _: None = Depends(requires("users.read_self"))):
    """Return the markdown content of a documentation page by slug."""
    entry = next((e for e in DOCS_INDEX if e[0] == slug), None)
    if not entry:
        raise HTTPException(404, f"Doc '{slug}' not found")

    _, title, rel_path, section = entry
    full_path = REPO_ROOT / rel_path

    if not full_path.exists():
        raise HTTPException(404, f"Doc file not found on disk: {rel_path}")

    return {
        "slug": slug,
        "title": title,
        "section": section,
        "content": full_path.read_text(encoding="utf-8"),
    }
