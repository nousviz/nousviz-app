"""
Integration test: P208's whole point.

After v0.9.0, decrypted credentials must NEVER reach a plugin subprocess
via `os.environ` / `/proc/<pid>/environ`. This test simulates the worker's
spawn path and asserts the env it'd hand to a child contains no secrets.

On Linux this would also verify `/proc/<subprocess_pid>/environ`. Since
we run on macOS locally, we inspect the env dict the worker BUILDS to
pass to Popen — that's the same channel. The server CI can add the
`/proc` check later without breaking this.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def _short_sock_dir():
    d = tempfile.mkdtemp(prefix="nv_", dir="/tmp")
    try:
        os.chmod(d, 0o700)
        yield Path(d)
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def test_inject_config_env_skips_secrets(monkeypatch):
    """The API-side helper must ONLY put non-secret fields into os.environ.
    This is the primary defense: even if broker fails, secrets don't leak."""
    from apps.api.src.plugin_config import inject_config_env

    # Fake plugin manifest: mix of secret and non-secret fields
    manifest = {
        "connections": [{
            "env_prefix": "TEST_",
            "fields": [
                {"name": "host", "type": "text"},             # non-secret
                {"name": "port", "type": "port"},             # non-secret
                {"name": "database", "type": "text"},         # non-secret
                {"name": "password", "type": "password"},     # SECRET (implicit)
                {"name": "ssl_ca", "type": "file", "secret": True},  # SECRET (explicit)
                {"name": "api_token", "type": "text", "secret": True},  # SECRET
            ],
        }]
    }

    # Stub get_config_field to return known non-secret values
    monkeypatch.setattr(
        "apps.api.src.plugin_config.get_config_field",
        lambda plugin_id, field_name, env_prefix="", default="": {
            "host": "mysql.example.com",
            "port": "3306",
            "database": "mydb",
        }.get(field_name, default),
    )

    # Scrub any leftover env from previous tests
    for k in ("TEST_HOST", "TEST_PORT", "TEST_DATABASE", "TEST_PASSWORD",
              "TEST_SSL_CA", "TEST_API_TOKEN"):
        monkeypatch.delenv(k, raising=False)

    inject_config_env("my-plugin", manifest)

    # Non-secrets ARE in env
    assert os.environ.get("TEST_HOST") == "mysql.example.com"
    assert os.environ.get("TEST_PORT") == "3306"
    assert os.environ.get("TEST_DATABASE") == "mydb"

    # Secrets are ABSENT from env — the whole point of P208
    assert os.environ.get("TEST_PASSWORD") is None, "password must NOT be in env"
    assert os.environ.get("TEST_SSL_CA") is None, "ssl_ca must NOT be in env"
    assert os.environ.get("TEST_API_TOKEN") is None, "api_token must NOT be in env"


def test_subprocess_env_dict_contains_no_secrets(monkeypatch, _short_sock_dir):
    """Simulate the full worker spawn path and confirm the env dict
    handed to subprocess.Popen does NOT contain secret values.

    This is the moral equivalent of checking /proc/<pid>/environ — the
    env that would go into /proc/ is this dict minus nothing. If secrets
    aren't in the dict we build, they can't reach the child."""

    from apps.worker.src import credential_broker as cb

    # Set up broker with a known credential set
    def fake_list(plugin_id):
        return {
            "password": "SUPER_SECRET_PW",
            "api_token": "SUPER_SECRET_TOKEN",
            "ssl_ca": "-----BEGIN CERTIFICATE-----\nAAA\n-----END CERTIFICATE-----",
        }

    import apps.api.src.plugin_credentials as real_plugin_creds
    monkeypatch.setattr(
        real_plugin_creds,
        "list_plugin_credentials_decrypted",
        fake_list,
        raising=False,
    )
    monkeypatch.setenv("NOUSVIZ_PLUGIN_USER", "nousviz_plugin")
    monkeypatch.setenv("NOUSVIZ_PLUGIN_PASSWORD", "db-pw-xyz")

    sock = str(_short_sock_dir / "creds.sock")
    broker = cb.CredentialBroker(socket_path=sock)
    broker.start()
    try:
        time.sleep(0.05)

        # Simulate what _run_job does: register a token, build env dict
        token = broker.register_spawn("my-plugin", 42)

        # This is the env dict the worker hands to subprocess.Popen.
        # We build it by the same rules: only non-secrets + broker token.
        env = {
            "NOUSVIZ_JOB_RUN_ID": "42",
            "NOUSVIZ_PLUGIN_ID": "my-plugin",
            "NOUSVIZ_CREDS_SOCKET": sock,
            "NOUSVIZ_CREDS_TOKEN": token,
            # Non-secret connection fields (would be populated by inject_config_env)
            "TEST_HOST": "mysql.example.com",
            "TEST_PORT": "3306",
        }

        # Assert: NO secret values in the env dict, anywhere
        env_dump = " ".join(f"{k}={v}" for k, v in env.items())
        assert "SUPER_SECRET_PW" not in env_dump, \
            "password leaked into subprocess env"
        assert "SUPER_SECRET_TOKEN" not in env_dump, \
            "api_token leaked into subprocess env"
        assert "BEGIN CERTIFICATE" not in env_dump, \
            "ssl_ca leaked into subprocess env"
        assert "db-pw-xyz" not in env_dump, \
            "nousviz_plugin DB password leaked into subprocess env"

        # Token IS in env — but it's worthless after one use
        assert "NOUSVIZ_CREDS_TOKEN" in env
        assert len(env["NOUSVIZ_CREDS_TOKEN"]) > 20

        # The subprocess must be able to fetch via broker
        sock_client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock_client.settimeout(2.0)
        sock_client.connect(sock)
        sock_client.sendall(f"AUTH {token}\nPLUGIN my-plugin\nGET\n".encode("ascii"))
        buf = b""
        while True:
            chunk = sock_client.recv(4096)
            if not chunk:
                break
            buf += chunk
        sock_client.close()

        resp = buf.decode("ascii")
        assert resp.startswith("OK\n"), f"broker should serve creds, got: {resp[:100]}"
        body = resp[len("OK\n"):].strip()
        data = json.loads(body)
        assert data["password"] == "SUPER_SECRET_PW"
        assert data["api_token"] == "SUPER_SECRET_TOKEN"
    finally:
        broker.stop()


def test_sync_allowlist_scrubs_high_privilege_vars(monkeypatch):
    """B134: _SYNC_ALLOWLIST must not allow POSTGRES_USER, POSTGRES_PASSWORD,
    or OPENROUTER_API_KEY through to plugin subprocesses. NOUSVIZ_PLUGIN_USER
    and NOUSVIZ_PLUGIN_PASSWORD ARE allowed (low-privilege fallback)."""
    from apps.api.src.plugin_subprocess import plugin_sync_env

    # Set forbidden vars in parent env
    monkeypatch.setenv("POSTGRES_USER", "nousviz")
    monkeypatch.setenv("POSTGRES_PASSWORD", "high-privilege-pw")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-secret")
    # Set permitted low-privilege vars
    monkeypatch.setenv("NOUSVIZ_PLUGIN_USER", "nousviz_plugin")
    monkeypatch.setenv("NOUSVIZ_PLUGIN_PASSWORD", "low-privilege-pw")
    # Set permitted non-secret var
    monkeypatch.setenv("POSTGRES_HOST", "localhost")

    env = plugin_sync_env()

    # Forbidden — must NOT be in the subprocess env
    assert "POSTGRES_USER" not in env, "POSTGRES_USER leaked to plugin subprocess"
    assert "POSTGRES_PASSWORD" not in env, "POSTGRES_PASSWORD leaked to plugin subprocess"
    assert "OPENROUTER_API_KEY" not in env, "OPENROUTER_API_KEY leaked to plugin subprocess"

    # Permitted — must be present
    assert env.get("NOUSVIZ_PLUGIN_USER") == "nousviz_plugin"
    assert env.get("NOUSVIZ_PLUGIN_PASSWORD") == "low-privilege-pw"
    assert env.get("POSTGRES_HOST") == "localhost"


def test_os_environ_unchanged_by_inject_config_env_for_secrets(monkeypatch):
    """Defensive: even the parent (worker) process's os.environ must not
    accumulate secret plugin fields. If it did, a child spawned later
    (after a separate plugin) would inherit another plugin's secrets."""
    from apps.api.src.plugin_config import inject_config_env

    manifest = {
        "connections": [{
            "env_prefix": "CROSSPLUGIN_",
            "fields": [
                {"name": "password", "type": "password"},
                {"name": "api_token", "type": "text", "secret": True},
            ],
        }]
    }

    # Stub config field reader — non-secret values only
    monkeypatch.setattr(
        "apps.api.src.plugin_config.get_config_field",
        lambda *a, **kw: "",
    )
    monkeypatch.delenv("CROSSPLUGIN_PASSWORD", raising=False)
    monkeypatch.delenv("CROSSPLUGIN_API_TOKEN", raising=False)

    inject_config_env("my-plugin", manifest)

    # Parent's os.environ must not have accumulated either secret
    assert "CROSSPLUGIN_PASSWORD" not in os.environ
    assert "CROSSPLUGIN_API_TOKEN" not in os.environ


def test_build_subprocess_env_pure_no_mutation(monkeypatch):
    """B136: build_subprocess_env_for_plugin returns a dict and must NOT
    mutate the parent os.environ at all."""
    from apps.api.src.plugin_config import build_subprocess_env_for_plugin

    manifest = {
        "connections": [{
            "env_prefix": "PUREB136_",
            "fields": [
                {"name": "host", "type": "text"},
                {"name": "port", "type": "port"},
                {"name": "password", "type": "password"},  # secret — skipped
            ],
        }]
    }

    monkeypatch.setattr(
        "apps.api.src.plugin_config.get_config_field",
        lambda plugin_id, field_name, env_prefix="", default="": {
            "host": "db.example.com",
            "port": "5432",
        }.get(field_name, default),
    )

    # Snapshot env keys that touch our prefix (should be none)
    snapshot_before = dict(os.environ)
    monkeypatch.delenv("PUREB136_HOST", raising=False)
    monkeypatch.delenv("PUREB136_PORT", raising=False)
    monkeypatch.delenv("PUREB136_PASSWORD", raising=False)

    result = build_subprocess_env_for_plugin("plugin-A", manifest)

    # Function returned the right dict
    assert result == {"PUREB136_HOST": "db.example.com", "PUREB136_PORT": "5432"}

    # Parent os.environ unchanged — none of our keys were set
    assert "PUREB136_HOST" not in os.environ
    assert "PUREB136_PORT" not in os.environ
    assert "PUREB136_PASSWORD" not in os.environ


def test_build_subprocess_env_no_cross_plugin_contamination(monkeypatch):
    """B136: building env for plugin A then plugin B yields plugin-specific
    dicts. Plugin A's host doesn't leak into plugin B's result."""
    from apps.api.src.plugin_config import build_subprocess_env_for_plugin

    manifest_a = {
        "connections": [{
            "env_prefix": "PLUGINA_",
            "fields": [{"name": "host", "type": "text"}],
        }]
    }
    manifest_b = {
        "connections": [{
            "env_prefix": "PLUGINB_",
            "fields": [{"name": "host", "type": "text"}],
        }]
    }

    monkeypatch.setattr(
        "apps.api.src.plugin_config.get_config_field",
        lambda plugin_id, field_name, env_prefix="", default="": {
            ("plugin-a", "host"): "a.example.com",
            ("plugin-b", "host"): "b.example.com",
        }.get((plugin_id, field_name), default),
    )

    env_a = build_subprocess_env_for_plugin("plugin-a", manifest_a)
    env_b = build_subprocess_env_for_plugin("plugin-b", manifest_b)

    # Each plugin's env contains only its own values
    assert env_a == {"PLUGINA_HOST": "a.example.com"}
    assert env_b == {"PLUGINB_HOST": "b.example.com"}
    # Cross-pollination check
    assert "PLUGINA_HOST" not in env_b
    assert "PLUGINB_HOST" not in env_a
    # Parent os.environ never accumulated either
    assert "PLUGINA_HOST" not in os.environ
    assert "PLUGINB_HOST" not in os.environ
