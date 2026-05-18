"""
Plugin manifest extension validator (v0.8.6).

Validates the `hooks:`, `actions:`, `setup_checklist:`, and new field-type
blocks introduced in v0.8.6. Called from the install route alongside the
existing `_validate_requires`.

All validators raise `ManifestValidationError` on rejection. The install
route catches this and returns a 400 with a clear message.
"""

from __future__ import annotations

import re
from typing import Any

from .plugin_hooks import ALLOWED_HOOKS
from .plugin_predicates import ALLOWED_PREDICATES


class ManifestValidationError(ValueError):
    """Raised when a plugin.yaml contains an invalid extension block."""


# ── P118: hooks: ──────────────────────────────────────────────────────


_TARGET_RE = re.compile(r"^[a-zA-Z_][\w.]*:[a-zA-Z_]\w*$")


def validate_hooks_block(plugin_id: str, block: Any) -> None:
    if block is None:
        return
    if not isinstance(block, dict):
        raise ManifestValidationError(
            f"plugin {plugin_id}: `hooks:` must be a mapping, got {type(block).__name__}"
        )
    for name, target in block.items():
        if name not in ALLOWED_HOOKS:
            raise ManifestValidationError(
                f"plugin {plugin_id}: unknown hook {name!r} — allowed: "
                + ", ".join(sorted(ALLOWED_HOOKS))
            )
        if not isinstance(target, str) or not _TARGET_RE.match(target):
            raise ManifestValidationError(
                f"plugin {plugin_id}: hook {name!r} target must be 'module:function', got {target!r}"
            )


# ── P119: actions: ────────────────────────────────────────────────────


ALLOWED_ACTION_SLOTS = frozenset({
    "settings_tab_footer",
    "plugin_page_header",
    "dashboard_header",
})
ALLOWED_ACTION_STYLES = frozenset({"primary", "secondary", "danger"})
ALLOWED_ACTION_METHODS = frozenset({"GET", "POST"})
_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
_ENDPOINT_RE = re.compile(r"^(GET|POST)\s+(/\S+)$")


def validate_actions_block(plugin_id: str, block: Any) -> None:
    if block is None:
        return
    if not isinstance(block, list):
        raise ManifestValidationError(
            f"plugin {plugin_id}: `actions:` must be a list"
        )
    seen_ids: set[str] = set()
    for idx, action in enumerate(block):
        where = f"actions[{idx}]"
        if not isinstance(action, dict):
            raise ManifestValidationError(f"plugin {plugin_id}: {where} must be a mapping")

        action_id = action.get("id")
        if not isinstance(action_id, str) or not _ID_RE.match(action_id):
            raise ManifestValidationError(
                f"plugin {plugin_id}: {where}.id must be kebab/snake case (got {action_id!r})"
            )
        if action_id in seen_ids:
            raise ManifestValidationError(
                f"plugin {plugin_id}: duplicate action id {action_id!r}"
            )
        seen_ids.add(action_id)

        label = action.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ManifestValidationError(
                f"plugin {plugin_id}: {where}.label must be a non-empty string"
            )

        slot = action.get("slot")
        if slot not in ALLOWED_ACTION_SLOTS:
            raise ManifestValidationError(
                f"plugin {plugin_id}: {where}.slot must be one of "
                + ", ".join(sorted(ALLOWED_ACTION_SLOTS))
                + f" (got {slot!r})"
            )

        style = action.get("style", "secondary")
        if style not in ALLOWED_ACTION_STYLES:
            raise ManifestValidationError(
                f"plugin {plugin_id}: {where}.style must be one of "
                + ", ".join(sorted(ALLOWED_ACTION_STYLES))
            )

        endpoint = action.get("endpoint", "")
        m = _ENDPOINT_RE.match(endpoint) if isinstance(endpoint, str) else None
        if not m:
            raise ManifestValidationError(
                f"plugin {plugin_id}: {where}.endpoint must be '<METHOD> <path>' "
                f"(got {endpoint!r})"
            )
        method, path = m.group(1), m.group(2)
        if method not in ALLOWED_ACTION_METHODS:
            raise ManifestValidationError(
                f"plugin {plugin_id}: {where}.endpoint method must be GET or POST"
            )
        allowed_prefixes = (
            f"/api/plugins/{plugin_id}/",
            f"/plugins/{plugin_id}/",
        )
        if not any(path.startswith(p) for p in allowed_prefixes):
            raise ManifestValidationError(
                f"plugin {plugin_id}: {where}.endpoint path must start with one of "
                f"{allowed_prefixes} (got {path!r})"
            )

        confirm = action.get("confirm", False)
        if confirm is not False and not isinstance(confirm, str):
            raise ManifestValidationError(
                f"plugin {plugin_id}: {where}.confirm must be false or a prompt string"
            )

        for pred_key in ("disabled_when", "visible_when"):
            pred = action.get(pred_key)
            if pred is None:
                continue
            if not isinstance(pred, str) or pred not in ALLOWED_PREDICATES:
                raise ManifestValidationError(
                    f"plugin {plugin_id}: {where}.{pred_key} must be one of "
                    + ", ".join(sorted(ALLOWED_PREDICATES))
                    + f" (got {pred!r})"
                )


# ── P121: setup_checklist: ────────────────────────────────────────────


ALLOWED_SHOW_UNTIL = frozenset({"all_done", "credentials_saved", "dismissed"})


def validate_setup_checklist_block(plugin_id: str, block: Any) -> None:
    if block is None:
        return
    if not isinstance(block, dict):
        raise ManifestValidationError(
            f"plugin {plugin_id}: `setup_checklist:` must be a mapping"
        )

    show_until = block.get("show_until", "all_done")
    if show_until not in ALLOWED_SHOW_UNTIL:
        raise ManifestValidationError(
            f"plugin {plugin_id}: setup_checklist.show_until must be one of "
            + ", ".join(sorted(ALLOWED_SHOW_UNTIL))
        )

    items = block.get("items")
    if not isinstance(items, list) or not items:
        raise ManifestValidationError(
            f"plugin {plugin_id}: setup_checklist.items must be a non-empty list"
        )

    seen_ids: set[str] = set()
    for idx, item in enumerate(items):
        where = f"setup_checklist.items[{idx}]"
        if not isinstance(item, dict):
            raise ManifestValidationError(f"plugin {plugin_id}: {where} must be a mapping")

        item_id = item.get("id")
        if not isinstance(item_id, str) or not _ID_RE.match(item_id):
            raise ManifestValidationError(
                f"plugin {plugin_id}: {where}.id must be kebab/snake case (got {item_id!r})"
            )
        if item_id in seen_ids:
            raise ManifestValidationError(
                f"plugin {plugin_id}: duplicate checklist item id {item_id!r}"
            )
        seen_ids.add(item_id)

        label = item.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ManifestValidationError(
                f"plugin {plugin_id}: {where}.label must be a non-empty string"
            )

        done_if = item.get("done_if")
        if not isinstance(done_if, str) or done_if not in ALLOWED_PREDICATES:
            raise ManifestValidationError(
                f"plugin {plugin_id}: {where}.done_if must be one of "
                + ", ".join(sorted(ALLOWED_PREDICATES))
                + f" (got {done_if!r})"
            )


# ── P120: field types ─────────────────────────────────────────────────


ALLOWED_FIELD_TYPES = frozenset({
    "text", "number", "password", "toggle", "select",
    # New in v0.8.6:
    "file", "port", "cron", "url",
})


def validate_field_types(plugin_id: str, connections: Any) -> None:
    """Validate type-specific field config. `connections:` is the full list
    from plugin.yaml — we iterate fields across all connections.
    """
    if not isinstance(connections, list):
        return
    for c_idx, conn in enumerate(connections):
        if not isinstance(conn, dict):
            continue
        fields = conn.get("fields") or []
        if not isinstance(fields, list):
            continue
        for f_idx, field in enumerate(fields):
            if not isinstance(field, dict):
                continue
            where = f"connections[{c_idx}].fields[{f_idx}]"
            ftype = field.get("type", "text")

            # B124 (v0.8.6.2): `secret:` is accepted on any field type.
            # Must be a bool if present. type: password is implicitly secret
            # and doesn't need the flag (backward compat).
            if "secret" in field and not isinstance(field["secret"], bool):
                raise ManifestValidationError(
                    f"plugin {plugin_id}: {where}: `secret:` must be true or false "
                    f"(got {field['secret']!r})"
                )

            if ftype not in ALLOWED_FIELD_TYPES:
                # Unknown type → treated as text at render time with a warning.
                # Validator logs it but doesn't reject — keeps forward/backward
                # compatibility with plugins declaring newer types we haven't
                # shipped yet.
                continue
            # Type-specific constraints:
            if ftype != "url" and "scheme" in field:
                raise ManifestValidationError(
                    f"plugin {plugin_id}: {where}: `scheme:` is only valid on type=url"
                )
            if ftype != "file":
                if "accept" in field:
                    raise ManifestValidationError(
                        f"plugin {plugin_id}: {where}: `accept:` is only valid on type=file"
                    )
                if "format_hint" in field:
                    raise ManifestValidationError(
                        f"plugin {plugin_id}: {where}: `format_hint:` is only valid on type=file"
                    )


# ── B151 (v0.9.4): frontend.components ────────────────────────────────


_COMPONENT_NAME_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")


def validate_frontend_components_block(plugin_id: str, block: Any) -> None:
    """Validate `frontend.components: [{name, path}]` (B151).

    Each component must declare:
      - name: PascalCase identifier (matches a valid React component name)
      - path: relative path inside the plugin dir, ending in `.js`

    Path traversal attempts (`..`) are rejected at install time. Absolute
    paths are rejected. Validation here is the FIRST line of defense; the
    runtime widget-serve endpoint validates again before serving.
    """
    if block is None:
        return
    if not isinstance(block, dict):
        raise ManifestValidationError(
            f"plugin {plugin_id}: `frontend:` must be a mapping, got {type(block).__name__}"
        )
    components = block.get("components")
    if components is None:
        return
    if not isinstance(components, list):
        raise ManifestValidationError(
            f"plugin {plugin_id}: `frontend.components:` must be a list, got {type(components).__name__}"
        )
    seen_names: set[str] = set()
    for i, item in enumerate(components):
        if not isinstance(item, dict):
            raise ManifestValidationError(
                f"plugin {plugin_id}: frontend.components[{i}] must be a mapping"
            )
        name = item.get("name")
        path = item.get("path")
        if not isinstance(name, str) or not _COMPONENT_NAME_RE.match(name):
            raise ManifestValidationError(
                f"plugin {plugin_id}: frontend.components[{i}].name must be PascalCase "
                f"(matching {_COMPONENT_NAME_RE.pattern}), got {name!r}"
            )
        if name in seen_names:
            raise ManifestValidationError(
                f"plugin {plugin_id}: frontend.components has duplicate name {name!r}"
            )
        seen_names.add(name)
        if not isinstance(path, str) or not path:
            raise ManifestValidationError(
                f"plugin {plugin_id}: frontend.components[{i}].path is required"
            )
        if path.startswith("/") or path.startswith("\\"):
            raise ManifestValidationError(
                f"plugin {plugin_id}: frontend.components[{i}].path must be relative, got {path!r}"
            )
        if ".." in path.split("/") or ".." in path.split("\\"):
            raise ManifestValidationError(
                f"plugin {plugin_id}: frontend.components[{i}].path must not contain '..' (path traversal)"
            )
        if not path.endswith(".js"):
            raise ManifestValidationError(
                f"plugin {plugin_id}: frontend.components[{i}].path must end with .js "
                f"(plugin authors compile their .tsx; commit the bundled .js), got {path!r}"
            )


# ── B312 (v0.10.3): oauth: ────────────────────────────────────────────


def validate_oauth_block(plugin_id: str, block: Any) -> None:
    """Validate `oauth.callback_handler: "module:function"` (B312).

    The block is optional. When present it must be a mapping with exactly
    one key, ``callback_handler``, whose value is a ``module:function``
    target string in the same shape we already enforce for ``hooks:``.

    The handler is invoked in-process by ``apps/api/src/routes/oauth.py``
    when the configured OAuth provider redirects the user's browser back
    to ``/api/oauth/callback/<plugin_id>``. Signature::

        def handle_callback(code: str, user_id: str) -> OAuthCallbackResult

    See ``sdk/nousviz_sdk/oauth.py`` for the result shape.
    """
    if block is None:
        return
    if not isinstance(block, dict):
        raise ManifestValidationError(
            f"plugin {plugin_id}: `oauth:` must be a mapping, got {type(block).__name__}"
        )
    extra = set(block.keys()) - {"callback_handler"}
    if extra:
        raise ManifestValidationError(
            f"plugin {plugin_id}: `oauth:` has unknown key(s) {sorted(extra)!r}; "
            f"only `callback_handler` is supported"
        )
    target = block.get("callback_handler")
    if target is None:
        raise ManifestValidationError(
            f"plugin {plugin_id}: `oauth.callback_handler` is required when `oauth:` is declared"
        )
    if not isinstance(target, str) or not _TARGET_RE.match(target):
        raise ManifestValidationError(
            f"plugin {plugin_id}: `oauth.callback_handler` must be 'module:function', got {target!r}"
        )


# ── Public entry point ────────────────────────────────────────────────


def validate_manifest_extensions(plugin_id: str, meta: dict) -> None:
    """Validate all v0.8.6+ manifest extensions. Call at install time."""
    validate_hooks_block(plugin_id, meta.get("hooks"))
    validate_actions_block(plugin_id, meta.get("actions"))
    validate_setup_checklist_block(plugin_id, meta.get("setup_checklist"))
    validate_field_types(plugin_id, meta.get("connections"))
    validate_frontend_components_block(plugin_id, meta.get("frontend"))
    validate_oauth_block(plugin_id, meta.get("oauth"))
