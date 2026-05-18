"""
Tests for B129 — env-safe helpers in the credential save path.

Covers:
  - _set_env_safe: strips nulls, tolerates putenv rejection
  - _validate_env_value: rejects newlines/null bytes/`=` in non-secret
    field values (these would corrupt .env)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── _set_env_safe ────────────────────────────────────────────────────


def test_set_env_safe_handles_plain_string(monkeypatch):
    from apps.api.src.routes.plugins import _set_env_safe
    monkeypatch.delenv("TEST_B129_KEY", raising=False)

    assert _set_env_safe("TEST_B129_KEY", "hello") is True
    assert os.environ["TEST_B129_KEY"] == "hello"

    monkeypatch.delenv("TEST_B129_KEY", raising=False)


def test_set_env_safe_strips_null_bytes(monkeypatch):
    from apps.api.src.routes.plugins import _set_env_safe
    monkeypatch.delenv("TEST_B129_NULL", raising=False)

    assert _set_env_safe("TEST_B129_NULL", "before\x00after") is True
    assert os.environ["TEST_B129_NULL"] == "beforeafter"
    assert "\x00" not in os.environ["TEST_B129_NULL"]

    monkeypatch.delenv("TEST_B129_NULL", raising=False)


def test_set_env_safe_coerces_non_string(monkeypatch):
    from apps.api.src.routes.plugins import _set_env_safe
    monkeypatch.delenv("TEST_B129_INT", raising=False)

    assert _set_env_safe("TEST_B129_INT", 3306) is True  # type: ignore[arg-type]
    assert os.environ["TEST_B129_INT"] == "3306"

    monkeypatch.delenv("TEST_B129_INT", raising=False)


def test_set_env_safe_returns_false_on_unsettable_value(monkeypatch):
    """Simulate putenv rejection by replacing the module's `os` binding
    with a shim whose `environ.__setitem__` raises. Scoped so it doesn't
    leak — only the plugins_module.os reference is swapped."""
    from apps.api.src.routes import plugins as plugins_module

    class FailingEnviron:
        def __setitem__(self, k, v):
            raise ValueError("simulated putenv rejection")
        # Support dict-like access the module might perform elsewhere:
        def get(self, k, default=None):
            return default
        def __contains__(self, k):
            return False

    class FakeOs:
        environ = FailingEnviron()

    monkeypatch.setattr(plugins_module, "os", FakeOs)
    result = plugins_module._set_env_safe("ANY_KEY_B129", "anything")
    assert result is False


# ── _validate_env_value ──────────────────────────────────────────────


def test_validate_env_value_accepts_plain_string():
    from apps.api.src.routes.plugins import _validate_env_value
    _validate_env_value("host", "mysql.example.com")
    _validate_env_value("port", "3306")
    _validate_env_value("user", "replica_joel_user")


def test_validate_env_value_rejects_newline():
    from apps.api.src.routes.plugins import _validate_env_value
    with pytest.raises(HTTPException) as exc:
        _validate_env_value("ssl_ca", "line1\nline2")
    assert exc.value.status_code == 400
    assert "newline" in exc.value.detail


def test_validate_env_value_rejects_carriage_return():
    from apps.api.src.routes.plugins import _validate_env_value
    with pytest.raises(HTTPException, match="carriage return"):
        _validate_env_value("f", "a\rb")


def test_validate_env_value_rejects_null_byte():
    from apps.api.src.routes.plugins import _validate_env_value
    with pytest.raises(HTTPException, match="null byte"):
        _validate_env_value("f", "a\x00b")


def test_validate_env_value_rejects_equals_sign():
    """`=` would split a KEY=VAL env line in ambiguous ways."""
    from apps.api.src.routes.plugins import _validate_env_value
    with pytest.raises(HTTPException, match="'=' character"):
        _validate_env_value("password", "p=ss")


def test_validate_env_value_rejection_message_suggests_secret_flag():
    from apps.api.src.routes.plugins import _validate_env_value
    with pytest.raises(HTTPException) as exc:
        _validate_env_value("ssl_ca", "BEGIN\nEND")
    assert "secret: true" in exc.value.detail


def test_validate_env_value_allows_pem_only_if_secret_path():
    """The validator is only called for NON-secret fields; PEM content
    in secret fields never hits this path. This test documents that
    contract — PEM passed to _validate_env_value rightly rejects."""
    from apps.api.src.routes.plugins import _validate_env_value
    pem = "-----BEGIN CERTIFICATE-----\nMIIC...\n-----END CERTIFICATE-----"
    with pytest.raises(HTTPException, match="newline"):
        _validate_env_value("cert", pem)


def test_validate_env_value_non_string_is_noop():
    from apps.api.src.routes.plugins import _validate_env_value
    # int / bool / None etc — handler str-coerces later; validator doesn't
    # need to reject these.
    _validate_env_value("port", 3306)  # type: ignore[arg-type]
    _validate_env_value("active", True)  # type: ignore[arg-type]
