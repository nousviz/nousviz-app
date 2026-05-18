"""Tests for B151 (v0.9.4) — frontend.components manifest validation
and the trust/revoke/list/serve endpoints' helpers.

Endpoint integration tests would require a TestClient with a real DB
fixture; here we cover the pure-logic guards (manifest validation,
component extraction, file path resolution).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── Manifest validation (validate_frontend_components_block) ──────────


def test_validate_frontend_block_accepts_well_formed():
    from apps.api.src.plugin_validation import validate_frontend_components_block
    block = {
        "components": [
            {"name": "FooWidget", "path": "widget/dist/FooWidget.js"},
            {"name": "BarPanel", "path": "widget/dist/BarPanel.js"},
        ]
    }
    validate_frontend_components_block("test-plugin", block)


def test_validate_frontend_block_accepts_none_or_empty():
    from apps.api.src.plugin_validation import validate_frontend_components_block
    validate_frontend_components_block("test-plugin", None)
    validate_frontend_components_block("test-plugin", {})
    validate_frontend_components_block("test-plugin", {"components": []})


def test_validate_frontend_rejects_lowercase_name():
    from apps.api.src.plugin_validation import (
        validate_frontend_components_block, ManifestValidationError,
    )
    block = {"components": [{"name": "fooWidget", "path": "widget/dist/Foo.js"}]}
    with pytest.raises(ManifestValidationError, match="PascalCase"):
        validate_frontend_components_block("test-plugin", block)


def test_validate_frontend_rejects_hyphenated_name():
    from apps.api.src.plugin_validation import (
        validate_frontend_components_block, ManifestValidationError,
    )
    block = {"components": [{"name": "Foo-Bar", "path": "widget/dist/Foo.js"}]}
    with pytest.raises(ManifestValidationError, match="PascalCase"):
        validate_frontend_components_block("test-plugin", block)


def test_validate_frontend_rejects_path_traversal():
    from apps.api.src.plugin_validation import (
        validate_frontend_components_block, ManifestValidationError,
    )
    block = {"components": [{"name": "Foo", "path": "../../etc/passwd"}]}
    with pytest.raises(ManifestValidationError, match="path traversal"):
        validate_frontend_components_block("test-plugin", block)


def test_validate_frontend_rejects_absolute_path():
    from apps.api.src.plugin_validation import (
        validate_frontend_components_block, ManifestValidationError,
    )
    block = {"components": [{"name": "Foo", "path": "/etc/passwd.js"}]}
    with pytest.raises(ManifestValidationError, match="must be relative"):
        validate_frontend_components_block("test-plugin", block)


def test_validate_frontend_rejects_non_js_extension():
    from apps.api.src.plugin_validation import (
        validate_frontend_components_block, ManifestValidationError,
    )
    block = {"components": [{"name": "Foo", "path": "widget/Foo.tsx"}]}
    with pytest.raises(ManifestValidationError, match="must end with .js"):
        validate_frontend_components_block("test-plugin", block)


def test_validate_frontend_rejects_empty_path():
    from apps.api.src.plugin_validation import (
        validate_frontend_components_block, ManifestValidationError,
    )
    block = {"components": [{"name": "Foo", "path": ""}]}
    with pytest.raises(ManifestValidationError, match="path is required"):
        validate_frontend_components_block("test-plugin", block)


def test_validate_frontend_rejects_duplicate_names():
    from apps.api.src.plugin_validation import (
        validate_frontend_components_block, ManifestValidationError,
    )
    block = {
        "components": [
            {"name": "Foo", "path": "widget/dist/A.js"},
            {"name": "Foo", "path": "widget/dist/B.js"},
        ]
    }
    with pytest.raises(ManifestValidationError, match="duplicate name"):
        validate_frontend_components_block("test-plugin", block)


def test_validate_frontend_rejects_non_dict_block():
    from apps.api.src.plugin_validation import (
        validate_frontend_components_block, ManifestValidationError,
    )
    with pytest.raises(ManifestValidationError, match="must be a mapping"):
        validate_frontend_components_block("test-plugin", "not a dict")


def test_validate_frontend_rejects_non_list_components():
    from apps.api.src.plugin_validation import (
        validate_frontend_components_block, ManifestValidationError,
    )
    with pytest.raises(ManifestValidationError, match="must be a list"):
        validate_frontend_components_block("test-plugin", {"components": "not a list"})


def test_validate_frontend_rejects_non_dict_component_entry():
    from apps.api.src.plugin_validation import (
        validate_frontend_components_block, ManifestValidationError,
    )
    with pytest.raises(ManifestValidationError, match="must be a mapping"):
        validate_frontend_components_block(
            "test-plugin",
            {"components": ["foo"]},
        )


def test_validate_frontend_block_runs_in_orchestrator():
    """validate_manifest_extensions must invoke the new validator."""
    from apps.api.src.plugin_validation import (
        validate_manifest_extensions, ManifestValidationError,
    )
    bad_meta = {
        "frontend": {
            "components": [{"name": "Foo", "path": "../../etc/passwd"}]
        }
    }
    with pytest.raises(ManifestValidationError, match="path traversal"):
        validate_manifest_extensions("test-plugin", bad_meta)


# ── _frontend_components_from_manifest ────────────────────────────────


def test_extract_components_returns_list():
    from apps.api.src.routes.plugins import _frontend_components_from_manifest
    meta = {
        "frontend": {
            "components": [
                {"name": "Foo", "path": "widget/dist/Foo.js"},
                {"name": "Bar", "path": "widget/dist/Bar.js"},
            ]
        }
    }
    out = _frontend_components_from_manifest(meta)
    assert len(out) == 2
    assert out[0]["name"] == "Foo"
    assert out[0]["path"] == "widget/dist/Foo.js"


def test_extract_components_returns_empty_when_absent():
    from apps.api.src.routes.plugins import _frontend_components_from_manifest
    assert _frontend_components_from_manifest({}) == []
    assert _frontend_components_from_manifest({"frontend": {}}) == []
    assert _frontend_components_from_manifest({"frontend": None}) == []


def test_extract_components_skips_malformed_entries():
    from apps.api.src.routes.plugins import _frontend_components_from_manifest
    meta = {
        "frontend": {
            "components": [
                {"name": "Foo", "path": "widget/Foo.js"},
                "not a dict",
                {"path": "widget/missing-name.js"},
                {"name": "Bar"},  # missing path
            ]
        }
    }
    out = _frontend_components_from_manifest(meta)
    assert len(out) == 1
    assert out[0]["name"] == "Foo"


def test_extract_components_handles_non_dict_input():
    from apps.api.src.routes.plugins import _frontend_components_from_manifest
    assert _frontend_components_from_manifest(None) == []
    assert _frontend_components_from_manifest("not a dict") == []
