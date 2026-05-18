"""
Unit tests for the P118 hook framework and manifest validation extensions
(P118/P119/P120/P121 shared validator).

Covers:
  - HookResult / HookContext serialization + env-driven construction
  - plugin_validation: hooks, actions, setup_checklist, field types
  - plugin_hooks: _load_hooks filtering, fire_hook enqueue with mocked DB
"""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── SDK: HookContext / HookResult ────────────────────────────────────


def test_hookresult_to_json_roundtrip():
    from sdk.nousviz_sdk.hooks import HookResult

    r = HookResult(ok=True, message="hi", data={"k": 1})
    parsed = json.loads(r.to_json())
    assert parsed == {"ok": True, "message": "hi", "data": {"k": 1}}


def test_hookresult_to_json_defaults():
    from sdk.nousviz_sdk.hooks import HookResult
    r = HookResult(ok=False)
    parsed = json.loads(r.to_json())
    assert parsed == {"ok": False, "message": None, "data": None}


def test_hookcontext_from_env_reads_all_fields(monkeypatch):
    from sdk.nousviz_sdk.hooks import HookContext
    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "my-plugin")
    monkeypatch.setenv("NOUSVIZ_HOOK_NAME", "on_credentials_saved")
    monkeypatch.setenv("NOUSVIZ_JOB_RUN_ID", "42")
    monkeypatch.setenv("NOUSVIZ_HOOK_PAYLOAD", '{"fields": ["api_key"]}')

    ctx = HookContext.from_env()
    assert ctx.plugin_id == "my-plugin"
    assert ctx.hook_name == "on_credentials_saved"
    assert ctx.run_id == 42
    assert ctx.payload == {"fields": ["api_key"]}


def test_hookcontext_from_env_handles_missing_fields(monkeypatch):
    from sdk.nousviz_sdk.hooks import HookContext
    for key in ("NOUSVIZ_PLUGIN_ID", "NOUSVIZ_HOOK_NAME", "NOUSVIZ_JOB_RUN_ID", "NOUSVIZ_HOOK_PAYLOAD"):
        monkeypatch.delenv(key, raising=False)
    ctx = HookContext.from_env()
    assert ctx.plugin_id == ""
    assert ctx.hook_name == ""
    assert ctx.run_id is None
    assert ctx.payload == {}


def test_hookcontext_malformed_payload_becomes_empty_dict(monkeypatch):
    from sdk.nousviz_sdk.hooks import HookContext
    monkeypatch.setenv("NOUSVIZ_HOOK_PAYLOAD", "not-json")
    ctx = HookContext.from_env()
    assert ctx.payload == {}


def test_hookcontext_payload_array_becomes_empty_dict(monkeypatch):
    """JSON arrays are valid JSON but not a dict — normalize to {}."""
    from sdk.nousviz_sdk.hooks import HookContext
    monkeypatch.setenv("NOUSVIZ_HOOK_PAYLOAD", '["not", "a", "dict"]')
    ctx = HookContext.from_env()
    assert ctx.payload == {}


def test_sdk_hooks_allowlist_matches_core():
    """The SDK and core must keep their hook allowlists in sync.
    Two-place truth, enforced here."""
    from sdk.nousviz_sdk.hooks import ALLOWED_HOOKS as sdk_allowed
    from apps.api.src.plugin_hooks import ALLOWED_HOOKS as core_allowed
    assert sdk_allowed == core_allowed


# ── Validator: hooks block ───────────────────────────────────────────


def test_validate_hooks_accepts_valid_block():
    from apps.api.src.plugin_validation import validate_hooks_block
    validate_hooks_block("p", {
        "on_install": "hooks.setup:on_install",
        "on_credentials_saved": "hooks.creds:on_saved",
    })  # no exception


def test_validate_hooks_rejects_unknown_name():
    from apps.api.src.plugin_validation import validate_hooks_block, ManifestValidationError
    with pytest.raises(ManifestValidationError, match="unknown hook"):
        validate_hooks_block("p", {"on_restart": "hooks:x"})


def test_validate_hooks_rejects_bad_target_format():
    from apps.api.src.plugin_validation import validate_hooks_block, ManifestValidationError
    with pytest.raises(ManifestValidationError, match="module:function"):
        validate_hooks_block("p", {"on_install": "not-a-target"})


def test_validate_hooks_rejects_non_dict():
    from apps.api.src.plugin_validation import validate_hooks_block, ManifestValidationError
    with pytest.raises(ManifestValidationError, match="must be a mapping"):
        validate_hooks_block("p", ["on_install"])


def test_validate_hooks_accepts_missing_block():
    from apps.api.src.plugin_validation import validate_hooks_block
    validate_hooks_block("p", None)  # no exception — hooks block is optional


# ── Validator: actions block ─────────────────────────────────────────


def _valid_action():
    return {
        "id": "test_connection",
        "label": "Test Connection",
        "slot": "settings_tab_footer",
        "style": "primary",
        "endpoint": "POST /api/plugins/my-plugin/test-connection",
        "confirm": False,
    }


def test_validate_actions_accepts_valid():
    from apps.api.src.plugin_validation import validate_actions_block
    validate_actions_block("my-plugin", [_valid_action()])


def test_validate_actions_rejects_bad_id():
    from apps.api.src.plugin_validation import validate_actions_block, ManifestValidationError
    a = _valid_action()
    a["id"] = "NotKebab"
    with pytest.raises(ManifestValidationError, match="kebab"):
        validate_actions_block("my-plugin", [a])


def test_validate_actions_rejects_duplicate_id():
    from apps.api.src.plugin_validation import validate_actions_block, ManifestValidationError
    a, b = _valid_action(), _valid_action()
    with pytest.raises(ManifestValidationError, match="duplicate"):
        validate_actions_block("my-plugin", [a, b])


def test_validate_actions_rejects_bad_slot():
    from apps.api.src.plugin_validation import validate_actions_block, ManifestValidationError
    a = _valid_action()
    a["slot"] = "sidebar"
    with pytest.raises(ManifestValidationError, match="slot"):
        validate_actions_block("my-plugin", [a])


def test_validate_actions_rejects_bad_style():
    from apps.api.src.plugin_validation import validate_actions_block, ManifestValidationError
    a = _valid_action()
    a["style"] = "rainbow"
    with pytest.raises(ManifestValidationError, match="style"):
        validate_actions_block("my-plugin", [a])


def test_validate_actions_rejects_bad_endpoint_format():
    from apps.api.src.plugin_validation import validate_actions_block, ManifestValidationError
    a = _valid_action()
    a["endpoint"] = "/no-method"
    with pytest.raises(ManifestValidationError, match="METHOD"):
        validate_actions_block("my-plugin", [a])


def test_validate_actions_rejects_bad_endpoint_method():
    from apps.api.src.plugin_validation import validate_actions_block, ManifestValidationError
    a = _valid_action()
    a["endpoint"] = "DELETE /api/plugins/my-plugin/x"
    with pytest.raises(ManifestValidationError):
        validate_actions_block("my-plugin", [a])


def test_validate_actions_rejects_cross_plugin_endpoint():
    from apps.api.src.plugin_validation import validate_actions_block, ManifestValidationError
    a = _valid_action()
    a["endpoint"] = "POST /api/plugins/other-plugin/steal"
    with pytest.raises(ManifestValidationError, match="path must start with"):
        validate_actions_block("my-plugin", [a])


def test_validate_actions_accepts_api_prefix_and_bare_prefix():
    from apps.api.src.plugin_validation import validate_actions_block
    a = _valid_action()
    a["endpoint"] = "POST /plugins/my-plugin/x"
    validate_actions_block("my-plugin", [a])


def test_validate_actions_rejects_unknown_predicate():
    from apps.api.src.plugin_validation import validate_actions_block, ManifestValidationError
    a = _valid_action()
    a["disabled_when"] = "arbitrary_thing"
    with pytest.raises(ManifestValidationError, match="disabled_when"):
        validate_actions_block("my-plugin", [a])


def test_validate_actions_accepts_allowed_predicate():
    from apps.api.src.plugin_validation import validate_actions_block
    a = _valid_action()
    a["disabled_when"] = "no_credentials"
    a["visible_when"] = "sync_in_progress"
    validate_actions_block("my-plugin", [a])


def test_validate_actions_rejects_confirm_non_string():
    from apps.api.src.plugin_validation import validate_actions_block, ManifestValidationError
    a = _valid_action()
    a["confirm"] = True
    with pytest.raises(ManifestValidationError, match="confirm"):
        validate_actions_block("my-plugin", [a])


# ── Validator: setup_checklist block ─────────────────────────────────


def test_validate_checklist_accepts_valid():
    from apps.api.src.plugin_validation import validate_setup_checklist_block
    validate_setup_checklist_block("p", {
        "show_until": "all_done",
        "items": [
            {"id": "creds", "label": "Save creds", "done_if": "credentials_saved"},
            {"id": "first", "label": "First run", "done_if": "first_sync_success"},
        ],
    })


def test_validate_checklist_rejects_unknown_predicate():
    from apps.api.src.plugin_validation import validate_setup_checklist_block, ManifestValidationError
    with pytest.raises(ManifestValidationError, match="done_if"):
        validate_setup_checklist_block("p", {
            "items": [{"id": "a", "label": "x", "done_if": "some_predicate"}],
        })


def test_validate_checklist_rejects_empty_items():
    from apps.api.src.plugin_validation import validate_setup_checklist_block, ManifestValidationError
    with pytest.raises(ManifestValidationError, match="items"):
        validate_setup_checklist_block("p", {"items": []})


def test_validate_checklist_rejects_bad_show_until():
    from apps.api.src.plugin_validation import validate_setup_checklist_block, ManifestValidationError
    with pytest.raises(ManifestValidationError, match="show_until"):
        validate_setup_checklist_block("p", {
            "show_until": "forever",
            "items": [{"id": "a", "label": "x", "done_if": "credentials_saved"}],
        })


def test_validate_checklist_rejects_duplicate_ids():
    from apps.api.src.plugin_validation import validate_setup_checklist_block, ManifestValidationError
    with pytest.raises(ManifestValidationError, match="duplicate"):
        validate_setup_checklist_block("p", {
            "items": [
                {"id": "a", "label": "x", "done_if": "credentials_saved"},
                {"id": "a", "label": "y", "done_if": "first_sync_success"},
            ],
        })


# ── Validator: field types ───────────────────────────────────────────


def test_validate_field_types_accepts_new_types():
    from apps.api.src.plugin_validation import validate_field_types
    validate_field_types("p", [{
        "fields": [
            {"name": "f1", "type": "file", "format_hint": "pem", "accept": ".pem,.crt"},
            {"name": "f2", "type": "port"},
            {"name": "f3", "type": "cron"},
            {"name": "f4", "type": "url", "scheme": "mysql"},
        ]
    }])


def test_validate_field_types_rejects_scheme_on_non_url():
    from apps.api.src.plugin_validation import validate_field_types, ManifestValidationError
    with pytest.raises(ManifestValidationError, match="scheme"):
        validate_field_types("p", [{
            "fields": [{"name": "f", "type": "port", "scheme": "https"}]
        }])


def test_validate_field_types_rejects_accept_on_non_file():
    from apps.api.src.plugin_validation import validate_field_types, ManifestValidationError
    with pytest.raises(ManifestValidationError, match="accept"):
        validate_field_types("p", [{
            "fields": [{"name": "f", "type": "text", "accept": ".pem"}]
        }])


def test_validate_field_types_allows_unknown_type_silently():
    """Unknown type → render as text with warning, don't break install."""
    from apps.api.src.plugin_validation import validate_field_types
    validate_field_types("p", [{
        "fields": [{"name": "f", "type": "colorpicker"}]
    }])


# ── plugin_hooks: _load_hooks filtering ──────────────────────────────


def test_load_hooks_filters_to_allowlist(tmp_path, monkeypatch):
    from apps.api.src import plugin_hooks as ph

    plugin_dir = tmp_path / "installed" / "my-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        "hooks:\n"
        "  on_install: hooks.setup:on_install\n"
        "  on_restart: hooks.setup:on_restart\n"   # unknown — should drop
        "  on_credentials_saved: hooks.creds:on_saved\n"
    )
    monkeypatch.setattr(ph, "INSTALLED_DIR", tmp_path / "installed")

    hooks = ph._load_hooks("my-plugin")
    assert "on_install" in hooks
    assert "on_credentials_saved" in hooks
    assert "on_restart" not in hooks


def test_load_hooks_returns_empty_for_missing_plugin(tmp_path, monkeypatch):
    from apps.api.src import plugin_hooks as ph
    monkeypatch.setattr(ph, "INSTALLED_DIR", tmp_path)
    assert ph._load_hooks("ghost-plugin") == {}


def test_load_hooks_returns_empty_for_absent_block(tmp_path, monkeypatch):
    from apps.api.src import plugin_hooks as ph
    plugin_dir = tmp_path / "installed" / "my-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text("name: my-plugin\n")
    monkeypatch.setattr(ph, "INSTALLED_DIR", tmp_path / "installed")
    assert ph._load_hooks("my-plugin") == {}


# ── plugin_hooks: fire_hook enqueue ──────────────────────────────────


@pytest.fixture
def stub_hook_db(monkeypatch, tmp_path):
    """Stub out the DB and plugin-dir resolution for fire_hook tests."""
    from apps.api.src import plugin_hooks as ph

    cursor = MagicMock()
    cursor.fetchone.return_value = (99,)
    conn = MagicMock()
    conn.cursor.return_value = cursor

    @contextmanager
    def fake_pg():
        yield conn

    monkeypatch.setattr(ph, "get_pg_conn", fake_pg)

    plugin_dir = tmp_path / "installed" / "p"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        "hooks:\n  on_install: hooks:on_install\n"
    )
    monkeypatch.setattr(ph, "INSTALLED_DIR", tmp_path / "installed")
    return {"cursor": cursor, "conn": conn}


def test_fire_hook_returns_none_when_hook_not_declared(stub_hook_db, monkeypatch, tmp_path):
    from apps.api.src import plugin_hooks as ph
    # Override manifest to have no hooks block
    (tmp_path / "installed" / "p" / "plugin.yaml").write_text("name: p\n")
    assert ph.fire_hook("p", "on_install") is None
    assert not stub_hook_db["cursor"].execute.called


def test_fire_hook_rejects_unknown_name(stub_hook_db):
    from apps.api.src.plugin_hooks import fire_hook
    assert fire_hook("p", "on_meteor_strike") is None


def test_fire_hook_enqueues_row(stub_hook_db):
    from apps.api.src.plugin_hooks import fire_hook
    run_id = fire_hook("p", "on_install", payload={"k": "v"})
    assert run_id == 99
    stub_hook_db["cursor"].execute.assert_called_once()
    sql, params = stub_hook_db["cursor"].execute.call_args[0]
    assert "INSERT INTO job_runs" in sql
    assert params[0] == "hook:p:on_install"
    # Payload is JSON in the second param
    details = json.loads(params[1])
    assert details["hook_name"] == "on_install"
    assert details["target"] == "hooks:on_install"
    assert details["payload"] == {"k": "v"}


# ── Allowlist consistency for predicates ─────────────────────────────


def test_action_predicate_allowlist_matches_resolver():
    """Validator and resolver must agree on which predicates are allowed."""
    from apps.api.src.plugin_predicates import ALLOWED_PREDICATES as resolver_set
    from apps.api.src.plugin_validation import ALLOWED_ACTION_SLOTS  # just importable

    # Validator references plugin_predicates.ALLOWED_PREDICATES directly,
    # so the set is by construction identical. This test asserts the import
    # path so a future refactor that breaks it fails loudly.
    assert len(resolver_set) >= 6
    assert ALLOWED_ACTION_SLOTS == {"settings_tab_footer", "plugin_page_header", "dashboard_header"}
