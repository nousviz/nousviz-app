"""
Unit tests for the credential broker (P208, v0.9.0).

Covers:
  - Token lifecycle (register, consume, expire, single-use, plugin-scoped)
  - Protocol parsing (well-formed / malformed requests)
  - Happy path via a real Unix socket with a fake credentials source
  - SDK client's broker fetch + cache
  - CredentialBrokerUnavailable raised when env is missing
"""

from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── Token lifecycle (no socket) ──────────────────────────────────────


def test_register_spawn_returns_unique_tokens():
    from apps.worker.src.credential_broker import CredentialBroker
    b = CredentialBroker(socket_path="/tmp/ignored.sock")
    t1 = b.register_spawn("plug", 1)
    t2 = b.register_spawn("plug", 2)
    assert t1 != t2
    assert len(t1) > 20  # base64 of 32 bytes


def test_consume_token_happy_path():
    from apps.worker.src.credential_broker import CredentialBroker
    b = CredentialBroker(socket_path="/tmp/ignored.sock")
    t = b.register_spawn("plug", 42)
    spawn = b._consume_token(t, "plug")
    assert spawn is not None
    assert spawn.plugin_id == "plug"
    assert spawn.run_id == 42


def test_consume_token_single_use():
    from apps.worker.src.credential_broker import CredentialBroker
    b = CredentialBroker(socket_path="/tmp/ignored.sock")
    t = b.register_spawn("plug", 1)
    assert b._consume_token(t, "plug") is not None
    # Second attempt: already consumed
    assert b._consume_token(t, "plug") is None


def test_consume_token_plugin_mismatch_denied_and_burned():
    from apps.worker.src.credential_broker import CredentialBroker
    b = CredentialBroker(socket_path="/tmp/ignored.sock")
    t = b.register_spawn("legit-plugin", 1)
    # Attacker plugin presents a token that isn't theirs
    assert b._consume_token(t, "evil-plugin") is None
    # And the token is burned even on failed mismatch
    assert b._consume_token(t, "legit-plugin") is None


def test_consume_token_expired():
    from apps.worker.src.credential_broker import CredentialBroker, _PendingSpawn
    b = CredentialBroker(socket_path="/tmp/ignored.sock")
    # Manually insert an expired token
    b._pending["expired_token"] = _PendingSpawn(
        plugin_id="plug", run_id=1, expires_at=time.time() - 1
    )
    assert b._consume_token("expired_token", "plug") is None


def test_consume_unknown_token():
    from apps.worker.src.credential_broker import CredentialBroker
    b = CredentialBroker(socket_path="/tmp/ignored.sock")
    assert b._consume_token("never-registered", "plug") is None


# ── Protocol parsing ─────────────────────────────────────────────────


def test_parse_request_happy():
    from apps.worker.src.credential_broker import CredentialBroker
    data = b"AUTH abc123\nPLUGIN my-plugin\nGET\n"
    token, plugin_id = CredentialBroker._parse_request(data)
    assert token == "abc123"
    assert plugin_id == "my-plugin"


def test_parse_request_missing_auth():
    from apps.worker.src.credential_broker import CredentialBroker, _BadRequest
    # Three lines present but first is not AUTH
    with pytest.raises(_BadRequest, match="AUTH"):
        CredentialBroker._parse_request(b"NOPE x\nPLUGIN y\nGET\n")


def test_parse_request_missing_plugin():
    from apps.worker.src.credential_broker import CredentialBroker, _BadRequest
    with pytest.raises(_BadRequest, match="PLUGIN"):
        CredentialBroker._parse_request(b"AUTH x\nNOPE y\nGET\n")


def test_parse_request_short_rejected():
    from apps.worker.src.credential_broker import CredentialBroker, _BadRequest
    with pytest.raises(_BadRequest, match="short"):
        CredentialBroker._parse_request(b"AUTH x\nGET\n")


def test_parse_request_missing_get():
    from apps.worker.src.credential_broker import CredentialBroker, _BadRequest
    with pytest.raises(_BadRequest, match="GET"):
        CredentialBroker._parse_request(b"AUTH x\nPLUGIN y\nBOGUS\n")


def test_parse_request_empty_field():
    from apps.worker.src.credential_broker import CredentialBroker, _BadRequest
    with pytest.raises(_BadRequest, match="empty"):
        CredentialBroker._parse_request(b"AUTH \nPLUGIN y\nGET\n")


def test_parse_request_non_ascii():
    from apps.worker.src.credential_broker import CredentialBroker, _BadRequest
    with pytest.raises(_BadRequest, match="non-ascii"):
        CredentialBroker._parse_request("AUTH 💥\nPLUGIN x\nGET\n".encode("utf-8"))


# ── End-to-end socket exchange with a stub decrypt ───────────────────


@pytest.fixture
def _short_sock_dir():
    """Unix socket paths are capped at ~104 chars; pytest's tmp_path on
    macOS is too long. Use /tmp/<short>/ for sockets only."""
    d = tempfile.mkdtemp(prefix="nv_", dir="/tmp")
    try:
        os.chmod(d, 0o700)
        yield Path(d)
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def broker_with_stub_decrypt(monkeypatch, _short_sock_dir):
    """Spin up a real broker on a temp socket; stub out the DB decrypt
    path to return a known credential set.
    """
    from apps.worker.src import credential_broker as cb

    def fake_list(plugin_id):
        if plugin_id == "empty-plug":
            return {}
        return {
            "password": "s3cret-pw",
            "api_token": "tok-xyz",
        }

    # Monkeypatch the import inside _fetch_credentials
    import apps.api.src.plugin_credentials as real_plugin_creds
    monkeypatch.setattr(
        real_plugin_creds,
        "list_plugin_credentials_decrypted",
        fake_list,
        raising=False,
    )

    # Fake __db__ env for the response
    monkeypatch.setenv("NOUSVIZ_PLUGIN_USER", "nousviz_plugin")
    monkeypatch.setenv("NOUSVIZ_PLUGIN_PASSWORD", "db-pw-xyz")

    sock = _short_sock_dir / "creds.sock"
    broker = cb.CredentialBroker(socket_path=str(sock))
    broker.start()
    # Give the accept thread a moment to bind.
    time.sleep(0.05)
    yield broker, str(sock)
    broker.stop()


def _broker_fetch(socket_path: str, token: str, plugin_id: str, timeout: float = 2.0) -> str:
    """Send a request, return the raw response text."""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect(socket_path)
    s.sendall(f"AUTH {token}\nPLUGIN {plugin_id}\nGET\n".encode("ascii"))
    buf = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
    s.close()
    return buf.decode("ascii")


def test_broker_end_to_end_ok(broker_with_stub_decrypt):
    broker, sock_path = broker_with_stub_decrypt
    token = broker.register_spawn("my-plugin", 1)
    resp = _broker_fetch(sock_path, token, "my-plugin")
    assert resp.startswith("OK\n")
    body = resp[len("OK\n"):].strip()
    data = json.loads(body)
    assert data["password"] == "s3cret-pw"
    assert data["api_token"] == "tok-xyz"
    assert data["__db__"]["user"] == "nousviz_plugin"
    assert data["__db__"]["password"] == "db-pw-xyz"


def test_broker_end_to_end_token_reuse_denied(broker_with_stub_decrypt):
    broker, sock_path = broker_with_stub_decrypt
    token = broker.register_spawn("my-plugin", 1)
    first = _broker_fetch(sock_path, token, "my-plugin")
    assert first.startswith("OK\n")
    second = _broker_fetch(sock_path, token, "my-plugin")
    assert second.startswith("DENIED\n")


def test_broker_end_to_end_plugin_mismatch_denied(broker_with_stub_decrypt):
    broker, sock_path = broker_with_stub_decrypt
    token = broker.register_spawn("legit", 1)
    resp = _broker_fetch(sock_path, token, "evil")
    assert resp.startswith("DENIED\n")
    # Original plugin can't reclaim the token either — it was burned
    retry = _broker_fetch(sock_path, token, "legit")
    assert retry.startswith("DENIED\n")


def test_broker_end_to_end_unknown_token(broker_with_stub_decrypt):
    _broker, sock_path = broker_with_stub_decrypt
    resp = _broker_fetch(sock_path, "fake-token", "whatever")
    assert resp.startswith("DENIED\n")


def test_broker_end_to_end_empty_credentials(broker_with_stub_decrypt):
    broker, sock_path = broker_with_stub_decrypt
    token = broker.register_spawn("empty-plug", 1)
    resp = _broker_fetch(sock_path, token, "empty-plug")
    assert resp.startswith("OK\n")
    body = resp[len("OK\n"):].strip()
    data = json.loads(body)
    # No credentials, but __db__ still present
    assert "__db__" in data
    assert len([k for k in data if k != "__db__"]) == 0


def test_broker_socket_file_permissions(broker_with_stub_decrypt):
    _broker, sock_path = broker_with_stub_decrypt
    st = os.stat(sock_path)
    # Owner RWX only (0o700), group/other get nothing
    mode = st.st_mode & 0o777
    assert mode == 0o700, f"expected 0o700, got 0o{mode:03o}"


# ── SDK broker client ────────────────────────────────────────────────


def test_sdk_client_raises_when_env_missing(monkeypatch):
    from sdk.nousviz_sdk._broker_client import _fetch_once, CredentialBrokerUnavailable

    monkeypatch.delenv("NOUSVIZ_CREDS_SOCKET", raising=False)
    monkeypatch.delenv("NOUSVIZ_CREDS_TOKEN", raising=False)
    monkeypatch.delenv("NOUSVIZ_PLUGIN_ID", raising=False)

    with pytest.raises(CredentialBrokerUnavailable, match="not set in environment"):
        _fetch_once()


def test_sdk_client_raises_when_socket_missing(monkeypatch, _short_sock_dir):
    from sdk.nousviz_sdk._broker_client import _fetch_once, CredentialBrokerUnavailable

    monkeypatch.setenv("NOUSVIZ_CREDS_SOCKET", str(_short_sock_dir / "nonexistent.sock"))
    monkeypatch.setenv("NOUSVIZ_CREDS_TOKEN", "whatever")
    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "test-plugin")

    with pytest.raises(CredentialBrokerUnavailable, match="Cannot reach credential broker"):
        _fetch_once()


def test_sdk_client_fetches_and_caches(monkeypatch, broker_with_stub_decrypt):
    from sdk.nousviz_sdk._broker_client import reset_cache_for_tests, get_cached

    broker, sock_path = broker_with_stub_decrypt
    token = broker.register_spawn("my-plugin", 1)

    reset_cache_for_tests()
    monkeypatch.setenv("NOUSVIZ_CREDS_SOCKET", sock_path)
    monkeypatch.setenv("NOUSVIZ_CREDS_TOKEN", token)
    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "my-plugin")

    creds = get_cached()
    assert creds["password"] == "s3cret-pw"
    assert creds["__db__"]["password"] == "db-pw-xyz"

    # Second call returns the cached copy — token is already consumed
    # by the broker, so if we were re-fetching, it'd fail.
    creds2 = get_cached()
    assert creds2 is creds


def test_sdk_client_denied_raises_broker_error(monkeypatch, broker_with_stub_decrypt):
    from sdk.nousviz_sdk._broker_client import _fetch_once, reset_cache_for_tests, CredentialBrokerError

    broker, sock_path = broker_with_stub_decrypt
    token = broker.register_spawn("legit", 1)

    reset_cache_for_tests()
    monkeypatch.setenv("NOUSVIZ_CREDS_SOCKET", sock_path)
    monkeypatch.setenv("NOUSVIZ_CREDS_TOKEN", token)
    # Caller identity mismatch → DENIED
    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "evil")

    with pytest.raises(CredentialBrokerError, match="denied"):
        _fetch_once()


def test_get_credential_via_public_api(monkeypatch, broker_with_stub_decrypt):
    """End-to-end: plugin code calls get_credential() exactly as documented."""
    from sdk.nousviz_sdk import get_credential
    from sdk.nousviz_sdk._broker_client import reset_cache_for_tests, reset_resolver_for_tests

    reset_resolver_for_tests()
    broker, sock_path = broker_with_stub_decrypt
    token = broker.register_spawn("my-plugin", 1)

    reset_cache_for_tests()
    monkeypatch.setenv("NOUSVIZ_CREDS_SOCKET", sock_path)
    monkeypatch.setenv("NOUSVIZ_CREDS_TOKEN", token)
    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "my-plugin")

    assert get_credential("my-plugin", "password") == "s3cret-pw"
    assert get_credential("my-plugin", "api_token") == "tok-xyz"
    assert get_credential("my-plugin", "nonexistent") is None


# ── In-process resolver (API context, P208 in-process fix) ───────────


def test_resolver_takes_precedence_over_broker(monkeypatch):
    """When a resolver is registered, get_cached uses it instead of the
    broker. This is the API-process path: plugin route handlers call
    get_credential, the resolver decrypts directly using the API's
    encryption key, no socket round-trip."""
    from sdk.nousviz_sdk._broker_client import (
        get_cached, register_resolver, reset_resolver_for_tests, reset_cache_for_tests,
    )

    reset_cache_for_tests()
    reset_resolver_for_tests()

    calls = []

    def fake_resolver(plugin_id):
        calls.append(plugin_id)
        return {"password": "from-resolver", "__db__": {"user": "x", "password": "y"}}

    register_resolver(fake_resolver)

    # No socket env set — broker would have raised. Resolver takes over.
    monkeypatch.delenv("NOUSVIZ_CREDS_SOCKET", raising=False)
    monkeypatch.delenv("NOUSVIZ_CREDS_TOKEN", raising=False)

    creds = get_cached(plugin_id="my-plugin")
    assert creds == {"password": "from-resolver", "__db__": {"user": "x", "password": "y"}}
    assert calls == ["my-plugin"]

    reset_resolver_for_tests()


def test_resolver_with_no_plugin_id_uses_core_sentinel(monkeypatch):
    """get_pg_conn() calls get_cached() without plugin_id — the resolver
    must still get called with a sentinel so it can return __db__."""
    from sdk.nousviz_sdk._broker_client import (
        get_cached, register_resolver, reset_resolver_for_tests, reset_cache_for_tests,
    )

    reset_cache_for_tests()
    reset_resolver_for_tests()

    received = []

    def fake_resolver(plugin_id):
        received.append(plugin_id)
        return {"__db__": {"user": "nousviz_plugin", "password": "pw"}}

    register_resolver(fake_resolver)
    monkeypatch.delenv("NOUSVIZ_PLUGIN_ID", raising=False)

    creds = get_cached()  # no plugin_id, no env
    assert creds == {"__db__": {"user": "nousviz_plugin", "password": "pw"}}
    assert received == ["__core__"]

    reset_resolver_for_tests()


def test_resolver_uses_env_plugin_id_when_no_arg(monkeypatch):
    """When NOUSVIZ_PLUGIN_ID is set in env (e.g., a worker subprocess
    where the resolver is somehow registered — uncommon but possible),
    fall back to that."""
    from sdk.nousviz_sdk._broker_client import (
        get_cached, register_resolver, reset_resolver_for_tests, reset_cache_for_tests,
    )

    reset_cache_for_tests()
    reset_resolver_for_tests()
    received = []

    def fake_resolver(plugin_id):
        received.append(plugin_id)
        return {"k": "v", "__db__": {"user": "u", "password": "p"}}

    register_resolver(fake_resolver)
    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "from-env")
    get_cached()  # no arg
    assert received == ["from-env"]
    reset_resolver_for_tests()


def test_subprocess_path_used_when_no_resolver(monkeypatch, broker_with_stub_decrypt):
    """Sanity: removing the resolver makes get_cached fall back to the
    broker. This is what worker-spawned subprocesses see."""
    from sdk.nousviz_sdk._broker_client import (
        get_cached, reset_resolver_for_tests, reset_cache_for_tests,
    )

    reset_resolver_for_tests()
    reset_cache_for_tests()

    broker, sock_path = broker_with_stub_decrypt
    token = broker.register_spawn("my-plugin", 1)

    monkeypatch.setenv("NOUSVIZ_CREDS_SOCKET", sock_path)
    monkeypatch.setenv("NOUSVIZ_CREDS_TOKEN", token)
    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", "my-plugin")

    creds = get_cached()
    # Came from broker → has stub's password
    assert creds["password"] == "s3cret-pw"
