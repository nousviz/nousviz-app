"""Tests for _get_deploy_key_path resolver (B204).

The resolver must only return a key on exact repo_url match. The legacy
host fallback caused silent wrong-key selection when multiple keys
shared a host (e.g. 12 github.com keys, one per repo).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


class _FakeCursor:
    """Minimal cursor stub: replays whichever rows the test set up."""

    def __init__(self, rows_for_url: dict[str, tuple] | None):
        self._rows = rows_for_url or {}
        self._last_row: tuple | None = None

    def execute(self, sql: str, params: tuple) -> None:
        # Only the WHERE repo_url = %s query should hit us (B204 dropped
        # the WHERE host = %s fallback).
        url = params[0]
        self._last_row = self._rows.get(url)

    def fetchone(self):
        return self._last_row


class _FakeConn:
    def __init__(self, rows_for_url):
        self._rows = rows_for_url

    def cursor(self):
        return _FakeCursor(self._rows)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _patch_resolver(monkeypatch, rows_for_url):
    from apps.api.src.routes import plugins as plugins_module

    monkeypatch.setattr(plugins_module, "get_pg_conn", lambda: _FakeConn(rows_for_url))
    monkeypatch.setenv("NOUSVIZ_ENCRYPTION_KEY", "00" * 32)

    class _StubFernet:
        def __init__(self, _key):
            pass

        def decrypt(self, _data: bytes) -> bytes:
            return b"-----BEGIN FAKE KEY-----\nstub\n-----END FAKE KEY-----\n"

    # Patch the Fernet class on its source module — the function does a
    # local `from cryptography.fernet import Fernet`, which resolves to
    # cryptography.fernet.Fernet at call time.
    import cryptography.fernet as _fernet_mod
    monkeypatch.setattr(_fernet_mod, "Fernet", _StubFernet)
    return plugins_module._get_deploy_key_path


def test_resolver_returns_key_for_exact_repo_match(monkeypatch, tmp_path):
    """An exact repo_url match returns a non-None temp file path."""
    # Production stores private_key_encrypted as TEXT; the resolver does
    # row[0].encode() before fernet.decrypt, so the stub uses str.
    rows = {"git@github.com:nousviz/plugin-foo.git": ("encrypted-fake",)}
    resolve = _patch_resolver(monkeypatch, rows)

    key_path = resolve("github.com", repo_url="git@github.com:nousviz/plugin-foo.git")
    assert key_path is not None
    assert Path(key_path).exists()
    Path(key_path).unlink()


def test_resolver_returns_none_for_unregistered_repo(monkeypatch):
    """B204: a sibling key on the same host must NOT be returned."""
    rows = {"git@github.com:nousviz/plugin-foo.git": ("encrypted-fake",)}
    resolve = _patch_resolver(monkeypatch, rows)

    # Asking for a different repo on the same host: no host fallback,
    # so resolver returns None.
    key_path = resolve("github.com", repo_url="git@github.com:nousviz/plugin-bar.git")
    assert key_path is None


def test_resolver_returns_none_when_no_repo_url(monkeypatch):
    """No repo_url provided → None (no host-only lookup)."""
    rows = {"git@github.com:nousviz/plugin-foo.git": ("encrypted-fake",)}
    resolve = _patch_resolver(monkeypatch, rows)

    assert resolve("github.com", repo_url=None) is None
    assert resolve("github.com") is None
