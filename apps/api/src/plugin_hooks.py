"""
Plugin hook dispatch — core side (P118, v0.8.6).

Two execution modes:

  fire_hook(plugin_id, hook_name, payload)
    — Async. Enqueues a `job_runs` row, jobs-worker picks it up and runs
      `python -m nousviz_sdk._hook_runner <target>` with the S107-hardened
      env. Use this for on_install / on_credentials_saved /
      on_first_run_success — the event already happened, the hook is a
      notification, and a failure shouldn't undo the event.

  run_hook_inline(plugin_id, hook_name, payload)
    — Sync. Runs the subprocess in the API process and returns the
      HookResult. Use this for on_uninstall where the plugin dir is about
      to be deleted — can't rely on a worker picking it up later. Capped
      at 30s so a misbehaving hook can't block uninstall forever.

Both modes are no-ops if the plugin doesn't declare the hook, so callers
fire unconditionally.

Hooks do NOT block their trigger — a failing on_credentials_saved does
not undo the credential save. Document this in the ticket so authors know
their hook must be idempotent.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

from .db import get_pg_conn
from .log_events import log_job_event

logger = logging.getLogger("nousviz.api.plugin_hooks")


# The closed allowlist — must match sdk/nousviz_sdk/hooks.py::ALLOWED_HOOKS.
# Duplicated here so core can validate without importing the SDK (the SDK
# would then have to be importable from the API runtime, which complicates
# deployment). Two-place truth, kept in sync by tests.
ALLOWED_HOOKS: frozenset[str] = frozenset({
    "on_install",
    "on_credentials_saved",
    "on_first_run_success",
    "on_uninstall",
})


REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALLED_DIR = REPO_ROOT / "plugins" / "installed"


def _load_hooks(plugin_id: str) -> dict[str, str]:
    """Read the `hooks:` block from plugin.yaml. Returns `{hook_name: target}`.

    Returns {} if the plugin is missing, the manifest is unreadable, or
    `hooks:` is absent. Never raises — callers fire hooks unconditionally.
    """
    manifest = INSTALLED_DIR / plugin_id / "plugin.yaml"
    if not manifest.exists():
        return {}
    try:
        data = yaml.safe_load(manifest.read_text()) or {}
    except Exception as exc:
        logger.warning("Could not parse %s for hooks: %s", manifest, exc)
        return {}
    block = data.get("hooks") or {}
    if not isinstance(block, dict):
        return {}
    # Filter to the allowlist defensively — validator should have done this
    # at install, but manifests on disk can drift.
    return {k: str(v) for k, v in block.items() if k in ALLOWED_HOOKS and isinstance(v, str)}


def fire_hook(plugin_id: str, hook_name: str, payload: dict[str, Any] | None = None) -> int | None:
    """Enqueue a hook run for `plugin_id`/`hook_name`. No-op if the plugin
    doesn't declare that hook.

    Returns the `job_runs.id` of the enqueued row, or None if no hook was
    registered / enqueue failed.
    """
    if hook_name not in ALLOWED_HOOKS:
        logger.warning("fire_hook rejected unknown hook_name %r for %s", hook_name, plugin_id)
        return None

    hooks = _load_hooks(plugin_id)
    target = hooks.get(hook_name)
    if not target:
        return None

    job_id = f"hook:{plugin_id}:{hook_name}"
    details = {
        "plugin_id": plugin_id,
        "hook_name": hook_name,
        "target": target,
        "payload": payload or {},
    }
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO job_runs (job_id, started_at, status, source, details)
                VALUES (%s, now(), 'queued', 'hook', %s::jsonb)
                RETURNING id
                """,
                (job_id, json.dumps(details)),
            )
            (run_id,) = cur.fetchone()
            conn.commit()
    except Exception as exc:
        logger.error("Failed to enqueue hook %s/%s: %s", plugin_id, hook_name, exc, exc_info=True)
        log_job_event(
            "error",
            f"Hook enqueue failed for {plugin_id}/{hook_name}",
            {"hook_name": hook_name, "error": str(exc)},
            plugin_id=plugin_id,
        )
        return None

    logger.info("Enqueued hook run %s for %s/%s", run_id, plugin_id, hook_name)
    return int(run_id)


def fire_first_sync_success_hook(plugin_id: str) -> int | None:
    """If this plugin has exactly one successful sync run, fire on_first_run_success.
    Idempotent: subsequent calls find 2+ successes and skip.

    Called from the jobs-worker right after writing a sync:<plugin> run with
    status=success, so the COUNT(*) includes the run that just completed.
    """
    job_id = f"sync:{plugin_id}"
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM job_runs WHERE job_id = %s AND status = 'success'",
                (job_id,),
            )
            (count,) = cur.fetchone()
    except Exception as exc:
        logger.warning("fire_first_sync_success_hook count failed for %s: %s", plugin_id, exc)
        return None
    if count != 1:
        return None
    return fire_hook(plugin_id, "on_first_run_success", payload={})


def run_hook_inline(
    plugin_id: str,
    hook_name: str,
    payload: dict[str, Any] | None = None,
    timeout_sec: int = 30,
) -> dict[str, Any] | None:
    """Run a hook synchronously in the API process. Returns the parsed
    HookResult dict or None if no hook is declared / run failed.

    Used by the uninstall flow where the plugin dir is removed immediately
    after — the async worker wouldn't have time to pick up the queued row.
    """
    import subprocess
    import sys
    from .plugin_subprocess import plugin_sync_env

    if hook_name not in ALLOWED_HOOKS:
        return None

    hooks = _load_hooks(plugin_id)
    target = hooks.get(hook_name)
    if not target:
        return None

    plugin_dir = INSTALLED_DIR / plugin_id
    if not plugin_dir.exists():
        return None

    env = plugin_sync_env()
    env["NOUSVIZ_PLUGIN_ID"] = plugin_id
    env["NOUSVIZ_HOOK_NAME"] = hook_name
    env["NOUSVIZ_HOOK_PAYLOAD"] = json.dumps(payload or {})

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "nousviz_sdk._hook_runner", target],
            cwd=str(plugin_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Inline hook %s/%s timed out after %ss", plugin_id, hook_name, timeout_sec)
        log_job_event(
            "warning",
            f"Hook {hook_name} timed out for {plugin_id}",
            {"hook_name": hook_name, "timeout_sec": timeout_sec},
            plugin_id=plugin_id,
        )
        return None

    last_line = (proc.stdout or "").strip().splitlines()[-1:] or [""]
    try:
        parsed = json.loads(last_line[0])
        if not isinstance(parsed, dict):
            parsed = {"ok": False, "message": "hook returned non-dict"}
    except Exception:
        parsed = {"ok": False, "message": f"hook stdout not JSON: {last_line[0][:100]}"}

    ok = bool(parsed.get("ok"))
    msg = parsed.get("message")
    level = "info" if ok else "error"
    log_job_event(
        level,
        f"Hook {hook_name} {'succeeded' if ok else 'failed'} for {plugin_id}"
        + (f": {msg}" if msg else ""),
        {
            "hook_name": hook_name,
            "exit_code": proc.returncode,
            "inline": True,
            "stderr_tail": (proc.stderr or "")[-500:] if not ok else None,
        },
        plugin_id=plugin_id,
    )
    return parsed
