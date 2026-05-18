"""Manifest-driven sync-script resolution (B201).

Single source of truth for "where is plugin <slug>'s sync script?" used
by both API routes (apps/api/src/routes/plugins.py + sync.py), the
worker (apps/worker/src/run_jobs.py), and the CLI (cli.py).

Reads `sync.script` from plugin.yaml; falls back to `src/sync.py` when
the manifest doesn't declare it — keeps legacy plugins working without
migration.

Leaf module: yaml + pathlib only, no upstream imports. Safe to import
from any half of the codebase without risking cycles.
"""

from __future__ import annotations

from pathlib import Path

import yaml


DEFAULT_SYNC_SCRIPT = "src/sync.py"


def resolve_sync_script(plugin_dir: Path) -> tuple[Path, str]:
    """Return (absolute_path, relative_path) for the plugin's sync script.

    Reads `sync.script` from `<plugin_dir>/plugin.yaml`; falls back to
    `src/sync.py`. Does NOT check whether the file exists — callers
    decide how to handle missing files (404 vs operator-friendly error).

    Defensive: missing manifest, malformed YAML, or non-string `script`
    value all degrade to the default rather than raising. Existence /
    correctness checks belong at the call site, where the right error
    shape (HTTPException vs CLI message) is known.
    """
    manifest_path = plugin_dir / "plugin.yaml"
    relative = DEFAULT_SYNC_SCRIPT
    if manifest_path.exists():
        try:
            meta = yaml.safe_load(manifest_path.read_text()) or {}
            sync = meta.get("sync") or {}
            declared = sync.get("script")
            if isinstance(declared, str) and declared.strip():
                relative = declared.strip()
        except Exception:
            pass
    return plugin_dir / relative, relative
