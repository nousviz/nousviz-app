"""Edition hook seams (MC-203).

Core never branches on the edition at feature call sites. Instead it
calls these hooks; the community defaults below make every hook a
no-op (allow / passthrough / enabled), and the managed add-on replaces
implementations via register() when it loads. Adding a future gated
feature means registering a new hook here — never editing core call
sites with `if managed` branches.

Core has zero entitlement knowledge: what a plan allows lives entirely
behind these seams.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Decision:
    """Outcome of an allow/deny hook. `reason` is customer-facing."""
    allowed: bool = True
    reason: str | None = None


ALLOW = Decision(True, None)


def _default_user_invite_allowed() -> Decision:
    return ALLOW


def _default_plugin_install_allowed(plugin_id: str) -> Decision:
    return ALLOW


def _default_resolve_smtp_config(cfg: dict | None) -> dict | None:
    return cfg


def _default_feature_enabled(name: str) -> bool:
    return True


_DEFAULTS: dict[str, Callable[..., Any]] = {
    "user_invite_allowed": _default_user_invite_allowed,
    "plugin_install_allowed": _default_plugin_install_allowed,
    "resolve_smtp_config": _default_resolve_smtp_config,
    "feature_enabled": _default_feature_enabled,
}

_registry: dict[str, Callable[..., Any]] = dict(_DEFAULTS)


def register(name: str, impl: Callable[..., Any]) -> None:
    """Replace a hook implementation. Unknown names are a hard error so
    a typo in the add-on fails at load time, not silently at call time."""
    if name not in _DEFAULTS:
        raise ValueError(
            f"Unknown hook {name!r}. Known hooks: {sorted(_DEFAULTS)}"
        )
    _registry[name] = impl


def reset() -> None:
    """Restore community defaults (tests + add-on unload)."""
    _registry.clear()
    _registry.update(_DEFAULTS)


def user_invite_allowed() -> Decision:
    """May this installation create one more user?"""
    return _registry["user_invite_allowed"]()


def plugin_install_allowed(plugin_id: str) -> Decision:
    """May this installation install `plugin_id`?"""
    return _registry["plugin_install_allowed"](plugin_id)


def resolve_smtp_config(cfg: dict | None) -> dict | None:
    """Resolve the SMTP transport. Community: the operator's own config,
    unchanged. Managed may substitute a relay per the entitlement."""
    return _registry["resolve_smtp_config"](cfg)


def feature_enabled(name: str) -> bool:
    """Is feature `name` available? Community: always yes."""
    return _registry["feature_enabled"](name)
