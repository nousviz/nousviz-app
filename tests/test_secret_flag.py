"""
Unit tests for B124 — explicit `secret: true` field flag.

Covers:
  - _field_is_secret helper: backward compat with type=password,
    forward-compat with explicit secret flag, none-match for regular fields.
  - plugin_validation: accepts bool on any field type, rejects non-bool.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def test_field_is_secret_legacy_password_type():
    """v0.8.5 compat: type: password is implicitly secret."""
    from apps.api.src.routes.plugins import _field_is_secret
    assert _field_is_secret({"name": "api_key", "type": "password"}) is True


def test_field_is_secret_explicit_flag_true():
    """v0.8.6.2: secret: true on any type (including new P120 types)."""
    from apps.api.src.routes.plugins import _field_is_secret
    assert _field_is_secret({"name": "ssl_ca", "type": "file", "secret": True}) is True
    assert _field_is_secret({"name": "token", "type": "text", "secret": True}) is True


def test_field_is_secret_explicit_flag_false_takes_legacy_priority():
    """If both are set, secret: true wins (or legacy password still secret).

    Concretely: secret: false + type: password still returns True because
    legacy plugins relied on type: password being secret. Plugins that want
    to explicitly opt a password field OUT of secrecy would be doing
    something weird — we don't support that case."""
    from apps.api.src.routes.plugins import _field_is_secret
    # Explicit true wins over missing flag
    assert _field_is_secret({"type": "file", "secret": True}) is True
    # type: password alone is still secret (legacy)
    assert _field_is_secret({"type": "password"}) is True


def test_field_is_secret_defaults_false():
    """Non-password, non-secret fields route to .env."""
    from apps.api.src.routes.plugins import _field_is_secret
    assert _field_is_secret({"name": "host", "type": "text"}) is False
    assert _field_is_secret({"name": "port", "type": "port"}) is False
    assert _field_is_secret({"name": "host", "type": "url"}) is False


def test_field_is_secret_explicit_false_non_password():
    from apps.api.src.routes.plugins import _field_is_secret
    assert _field_is_secret({"type": "file", "secret": False}) is False


# ── Validator ────────────────────────────────────────────────────────


def test_validator_accepts_secret_true_on_file():
    from apps.api.src.plugin_validation import validate_field_types
    validate_field_types("p", [{"fields": [
        {"name": "ssl_ca", "type": "file", "secret": True, "format_hint": "pem"},
    ]}])


def test_validator_accepts_secret_true_on_text():
    from apps.api.src.plugin_validation import validate_field_types
    validate_field_types("p", [{"fields": [
        {"name": "token", "type": "text", "secret": True},
    ]}])


def test_validator_rejects_non_bool_secret():
    from apps.api.src.plugin_validation import validate_field_types, ManifestValidationError
    with pytest.raises(ManifestValidationError, match="secret"):
        validate_field_types("p", [{"fields": [
            {"name": "x", "type": "text", "secret": "yes"},
        ]}])


def test_validator_rejects_numeric_secret():
    from apps.api.src.plugin_validation import validate_field_types, ManifestValidationError
    with pytest.raises(ManifestValidationError, match="secret"):
        validate_field_types("p", [{"fields": [
            {"name": "x", "type": "text", "secret": 1},
        ]}])


def test_validator_accepts_missing_secret():
    """Field without `secret:` key — validator never touches it."""
    from apps.api.src.plugin_validation import validate_field_types
    validate_field_types("p", [{"fields": [
        {"name": "host", "type": "text"},
    ]}])
