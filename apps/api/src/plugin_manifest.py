"""B247 (v0.9.10.6): plugin.yaml `permissions:` block parser.

The block's grammar:

    permissions:
      default: read | write | configure | admin
      routes:
        - path: <glob, optional>
          method: <HTTP method, optional>
          level: read | write | configure | admin

`default` is the per-router fallback. `routes:` entries override the
default for matching (method, path) pairs. The first matching entry
wins; method-only and path-only matches are allowed.

The parser is **strict** — unknown levels, missing required keys, and
non-string globs raise. Plugins that don't declare `permissions:` get
None back from `parse()` and the loader falls back to legacy defaults.

This module is import-safe with no FastAPI / DB dependencies — it can
be unit-tested without spinning up the API.
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from typing import Any, Optional

# Permission levels in increasing privilege order. Each plugin's
# permission strings are `plugin.<slug>.<level>` (B247 phase 2).
LEVELS: tuple[str, ...] = ("read", "write", "configure", "admin")

VALID_HTTP_METHODS: frozenset[str] = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})


class ManifestPermissionsError(ValueError):
    """Raised on invalid `permissions:` block. The message describes
    what's wrong and what the operator should fix in plugin.yaml."""


@dataclass(frozen=True)
class PermissionRule:
    """A single rule from a manifest's `permissions.routes` list, plus
    the implicit default-everything rule. Path/method may be None
    meaning "any". `level` is one of LEVELS."""
    method: Optional[str]
    path_glob: Optional[str]
    level: str

    def matches(self, method: str, path: str) -> bool:
        """True iff this rule applies to the given (method, path)."""
        if self.method is not None and self.method != method.upper():
            return False
        if self.path_glob is not None and not fnmatch.fnmatchcase(path, self.path_glob):
            return False
        return True


@dataclass(frozen=True)
class PermissionsConfig:
    """Parsed `permissions:` block. The default rule is always last —
    callers iterate rules in order and use the first match.
    """
    default_level: str
    route_rules: tuple[PermissionRule, ...]

    def resolve(self, method: str, path: str) -> str:
        """Return the level that should apply to (method, path)."""
        for rule in self.route_rules:
            if rule.matches(method, path):
                return rule.level
        return self.default_level


def parse(block: Any) -> Optional[PermissionsConfig]:
    """Parse a manifest's `permissions:` block.

    Returns None if `block` is None or {} (no declaration → loader
    falls back to legacy method-derived defaults).

    Raises `ManifestPermissionsError` on invalid input.
    """
    if block is None or block == {}:
        return None
    if not isinstance(block, dict):
        raise ManifestPermissionsError(
            f"`permissions:` must be a mapping, got {type(block).__name__}"
        )

    default_level = block.get("default", "read")
    if not isinstance(default_level, str):
        raise ManifestPermissionsError(
            f"`permissions.default` must be a string, got {type(default_level).__name__}"
        )
    if default_level not in LEVELS:
        raise ManifestPermissionsError(
            f"`permissions.default` is {default_level!r}; must be one of {list(LEVELS)}"
        )

    routes_raw = block.get("routes", [])
    if not isinstance(routes_raw, list):
        raise ManifestPermissionsError(
            f"`permissions.routes` must be a list, got {type(routes_raw).__name__}"
        )

    route_rules: list[PermissionRule] = []
    for i, entry in enumerate(routes_raw):
        if not isinstance(entry, dict):
            raise ManifestPermissionsError(
                f"`permissions.routes[{i}]` must be a mapping, got {type(entry).__name__}"
            )
        level = entry.get("level")
        if not isinstance(level, str) or level not in LEVELS:
            raise ManifestPermissionsError(
                f"`permissions.routes[{i}].level` is {level!r}; must be one of {list(LEVELS)}"
            )
        path_glob = entry.get("path")
        if path_glob is not None and not isinstance(path_glob, str):
            raise ManifestPermissionsError(
                f"`permissions.routes[{i}].path` must be a string glob (or omitted), got {type(path_glob).__name__}"
            )
        method = entry.get("method")
        if method is not None:
            if not isinstance(method, str):
                raise ManifestPermissionsError(
                    f"`permissions.routes[{i}].method` must be a string (or omitted), got {type(method).__name__}"
                )
            method_upper = method.upper()
            if method_upper not in VALID_HTTP_METHODS:
                raise ManifestPermissionsError(
                    f"`permissions.routes[{i}].method` is {method!r}; must be one of {sorted(VALID_HTTP_METHODS)}"
                )
            method = method_upper
        if path_glob is None and method is None:
            raise ManifestPermissionsError(
                f"`permissions.routes[{i}]` must specify at least one of `path` or `method`"
            )
        route_rules.append(
            PermissionRule(method=method, path_glob=path_glob, level=level)
        )

    return PermissionsConfig(
        default_level=default_level,
        route_rules=tuple(route_rules),
    )


# ── Permission-string derivation ────────────────────────────────────────

# Plugin slug must match the `name` field in plugin.yaml. Loader passes
# whatever discover_plugins() found; we sanity-check here so a bogus
# slug can't poison the permissions catalog.
_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def permission_string(slug: str, level: str) -> str:
    """Return `plugin.<slug>.<level>`.

    Raises if slug or level are invalid.
    """
    if not isinstance(slug, str) or not _SLUG_RE.match(slug):
        raise ManifestPermissionsError(
            f"plugin slug {slug!r} must match {_SLUG_RE.pattern}"
        )
    if level not in LEVELS:
        raise ManifestPermissionsError(
            f"level {level!r}; must be one of {list(LEVELS)}"
        )
    return f"plugin.{slug}.{level}"


def all_permission_strings(slug: str) -> list[str]:
    """Return all permission strings for a plugin (one per level).
    Used by the catalog to register the full set even before any route
    references a given level."""
    return [permission_string(slug, lvl) for lvl in LEVELS]
