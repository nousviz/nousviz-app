"""B215 (v0.9.10.2): typed responses for /api/sync/* (setup + health-check).

The sync trigger endpoint (POST /api/plugins/{id}/sync) already declares
its own `SyncResponse` model in routes/sync.py from B205 — this module
covers only the two remaining handlers.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PluginScriptRunResponse(BaseModel):
    """Result of running a plugin's setup_schema.py or health_check.py.

    Both endpoints return the same shape: subprocess exit code plus
    combined stdout+stderr. `status` is 'success' on returncode 0,
    'error' otherwise. Used by the plugin Settings tab to surface the
    setup/health output to the operator.
    """
    status: str = Field(..., description="'success' | 'error' (derived from subprocess exit code).")
    output: str = Field(..., description="Combined stdout + stderr from the plugin script.")
    exit_code: int = Field(..., description="The subprocess exit code.")
