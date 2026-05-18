"""
SDK-internal hook runner. Invoked by the NousViz jobs-worker as:

    python -m nousviz_sdk._hook_runner <module>:<function>

It loads the function, builds a HookContext from env vars, calls it, and
prints the HookResult as JSON on the final line of stdout (the worker
parses this). Exits 0 on ok=True, 1 on ok=False or any raised exception.

Plugins never call this directly — they just implement the hook function
and reference it from plugin.yaml.
"""

from __future__ import annotations

import importlib
import json
import sys
import traceback
from pathlib import Path

# Ensure the plugin dir is on sys.path — the worker launches this with
# cwd = plugin_dir, so we add cwd explicitly for imports like
# `hooks.creds:on_saved` (module="hooks.creds") to resolve.
sys.path.insert(0, str(Path.cwd()))

from .hooks import HookContext, HookResult


def _parse_target(target: str) -> tuple[str, str]:
    if ":" not in target:
        raise ValueError(f"Hook target must be 'module:function', got {target!r}")
    module, func = target.rsplit(":", 1)
    if not module or not func:
        raise ValueError(f"Hook target has empty module or function: {target!r}")
    return module, func


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "message": "missing hook target arg"}))
        return 1

    target = sys.argv[1]
    ctx = HookContext.from_env()

    try:
        module_name, func_name = _parse_target(target)
        module = importlib.import_module(module_name)
        fn = getattr(module, func_name, None)
        if fn is None:
            result = HookResult(
                ok=False,
                message=f"function {func_name!r} not found in module {module_name!r}",
            )
            print(result.to_json())
            return 1
        raw = fn(ctx)
        if raw is None:
            result = HookResult(ok=True, message=None)
        elif isinstance(raw, HookResult):
            result = raw
        elif isinstance(raw, dict):
            result = HookResult(
                ok=bool(raw.get("ok", True)),
                message=raw.get("message"),
                data=raw.get("data"),
            )
        else:
            result = HookResult(
                ok=False,
                message=f"hook returned unexpected type {type(raw).__name__}, expected HookResult",
            )
    except Exception as exc:
        tb = traceback.format_exc()
        result = HookResult(
            ok=False,
            message=f"{exc.__class__.__name__}: {exc}",
            data={"traceback": tb[-2000:]},
        )
        print(result.to_json())
        return 1

    print(result.to_json())
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
