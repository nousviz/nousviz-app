"""
nousviz_sdk.hooks — Lifecycle hook contract for plugins (P118, v0.8.6).

Plugins declare Python lifecycle callbacks in `plugin.yaml`:

    hooks:
      on_install:             hooks.setup:on_install
      on_credentials_saved:   hooks.creds:on_saved
      on_first_run_success:   hooks.setup:on_first_ok
      on_uninstall:           hooks.setup:on_uninstall

The referenced function must accept a single `HookContext` argument and
return a `HookResult`. Core runs the hook in the jobs-worker subprocess
(same S107-hardened env as sync scripts), records the outcome in
`job_runs`, and surfaces terminal events in `app_logs`.

Example hook:

    from nousviz_sdk.hooks import HookContext, HookResult

    def on_saved(ctx: HookContext) -> HookResult:
        # Plugin-specific work (ping a remote, write a setting, etc.)
        return HookResult(ok=True, message="Credentials acknowledged")

Raising exceptions is equivalent to returning `HookResult(ok=False, ...)` —
the worker will capture the traceback in `job_runs.error`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from typing import Any


# The closed allowlist of hook names. Must match core's validator.
# Keep this list and docs/plugin-architecture.md in lockstep.
ALLOWED_HOOKS: frozenset[str] = frozenset({
    "on_install",
    "on_credentials_saved",
    "on_first_run_success",
    "on_uninstall",
})


@dataclass
class HookContext:
    """Everything a hook needs to know about its invocation.

    Values are read from env vars set by the jobs-worker when spawning
    the hook subprocess. Plugins should not construct these themselves —
    use `HookContext.from_env()`.
    """

    plugin_id: str
    hook_name: str
    run_id: int | None = None
    # Free-form data the worker passes through (e.g. the saved credential
    # field names for on_credentials_saved — plugins decide what to do with it).
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "HookContext":
        import json

        plugin_id = os.environ.get("NOUSVIZ_PLUGIN_ID", "")
        hook_name = os.environ.get("NOUSVIZ_HOOK_NAME", "")
        run_id_raw = os.environ.get("NOUSVIZ_JOB_RUN_ID")
        run_id = int(run_id_raw) if run_id_raw and run_id_raw.isdigit() else None
        payload_raw = os.environ.get("NOUSVIZ_HOOK_PAYLOAD") or "{}"
        try:
            payload = json.loads(payload_raw)
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}
        return cls(
            plugin_id=plugin_id,
            hook_name=hook_name,
            run_id=run_id,
            payload=payload,
        )


@dataclass
class HookResult:
    """What a hook returns. Serialized back to the worker on stdout."""

    ok: bool
    message: str | None = None
    data: dict[str, Any] | None = None

    def to_json(self) -> str:
        import json
        return json.dumps(asdict(self))
