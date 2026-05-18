"""
Internal SDK client for the NousViz credential broker (and resolver registry).

Plugin authors do not use this module directly — they call
`nousviz_sdk.get_credential(...)` and the SDK dispatches through here.

## Two execution contexts

Plugin code runs in **two** different process types:

  1. **Subprocess** (sync scripts, hook handlers): spawned by the
     jobs-worker, gets a one-shot broker token in env. SDK reads
     `NOUSVIZ_CREDS_SOCKET` + `NOUSVIZ_CREDS_TOKEN` and exchanges over
     the Unix socket. This is the "broker client" path.

  2. **In-process** (plugin api/routes.py loaded by the API): runs in
     the FastAPI worker. No broker token in env. The API process is
     trusted core code with the encryption key already, so it can
     resolve credentials directly via a registered resolver instead of
     bouncing through the broker.

The `register_resolver()` API lets the core API process plug a direct
resolver in at startup. Subprocesses don't register a resolver, so they
fall through to the broker client. Plugin authors call
`get_credential()` and don't see which path was used.

## Failure modes

- Subprocess: `NOUSVIZ_CREDS_SOCKET` / `NOUSVIZ_CREDS_TOKEN` missing →
  `CredentialBrokerUnavailable`. Means the plugin is being run outside
  a NousViz-spawned subprocess (manual `python sync.py`, pytest etc.).
- Subprocess: broker `DENIED` / `ERROR` → `CredentialBrokerError`.
- In-process API: registered resolver raises → propagates to the caller.
"""

from __future__ import annotations

import json
import logging
import os
import socket
from typing import Any, Callable, Optional

logger = logging.getLogger("nousviz_sdk._broker_client")

# Populated on first access in subprocess context. Stays for the
# subprocess's lifetime. Keys: credential field names as stored in the
# credentials table. Special key "__db__" carries {"user", "password"}
# for the nousviz_plugin role.
_CACHE: dict[str, Any] | None = None

# Resolver registry — the API process registers an in-process resolver
# at startup. Signature: resolver(plugin_id) -> dict[str, Any] including
# decrypted credentials and (optionally) the special "__db__" key.
# When None (default), subprocess broker path is used.
_RESOLVER: Optional[Callable[[str], dict[str, Any]]] = None


def register_resolver(resolver: Callable[[str], dict[str, Any]]) -> None:
    """Register an in-process credential resolver.

    Used by the NousViz API process at startup to bypass the broker
    (which isn't reachable from in-process plugin route handlers because
    they don't have a token). The resolver should accept a plugin_id and
    return a dict matching the broker's response shape.

    Plugin authors should NOT call this. Calling it from plugin code is
    a no-op security-wise (you can already read everything in your own
    process), but it's not part of the supported API.
    """
    global _RESOLVER
    _RESOLVER = resolver


def reset_resolver_for_tests() -> None:
    """Test-only: unregister any resolver."""
    global _RESOLVER
    _RESOLVER = None


class CredentialBrokerUnavailable(RuntimeError):
    """Raised when the broker socket is not reachable. Typically means
    the plugin is running outside a NousViz-spawned subprocess."""


class CredentialBrokerError(RuntimeError):
    """Raised when the broker returns DENIED or ERROR."""


def _socket_recv_all(conn: socket.socket, max_bytes: int = 64 * 1024) -> bytes:
    """Read until EOF or max_bytes. Broker closes the connection after
    sending the response."""
    buf = b""
    while len(buf) < max_bytes:
        chunk = conn.recv(4096)
        if not chunk:
            break
        buf += chunk
    return buf


def _fetch_once() -> dict[str, Any]:
    """Open socket, authenticate, receive credentials JSON, return dict.

    Raises CredentialBrokerUnavailable if socket/token env missing.
    Raises CredentialBrokerError if broker responds DENIED / ERROR.
    """
    socket_path = os.environ.get("NOUSVIZ_CREDS_SOCKET")
    token = os.environ.get("NOUSVIZ_CREDS_TOKEN")
    plugin_id = os.environ.get("NOUSVIZ_PLUGIN_ID")

    if not socket_path or not token or not plugin_id:
        raise CredentialBrokerUnavailable(
            "NOUSVIZ_CREDS_SOCKET / NOUSVIZ_CREDS_TOKEN / NOUSVIZ_PLUGIN_ID "
            "not set in environment. This usually means your plugin code "
            "is running outside a NousViz-spawned subprocess. Plugin "
            "credentials are only available when the NousViz jobs-worker "
            "has spawned you with a broker token."
        )

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    try:
        try:
            sock.connect(socket_path)
        except (FileNotFoundError, ConnectionRefusedError) as exc:
            raise CredentialBrokerUnavailable(
                f"Cannot reach credential broker at {socket_path}: {exc}. "
                f"Is the NousViz jobs-worker running?"
            ) from exc

        request = f"AUTH {token}\nPLUGIN {plugin_id}\nGET\n".encode("ascii")
        sock.sendall(request)

        response = _socket_recv_all(sock)
        text = response.decode("ascii", errors="replace")
    finally:
        sock.close()

    # Parse response: "OK\n<json>\n" or "DENIED\n<reason>\n" or "ERROR\n<reason>\n"
    lines = text.split("\n", 1)
    if not lines:
        raise CredentialBrokerError("empty broker response")

    header = lines[0].strip()
    body = lines[1] if len(lines) > 1 else ""

    if header == "OK":
        try:
            return json.loads(body.strip())
        except json.JSONDecodeError as exc:
            raise CredentialBrokerError(f"broker returned invalid JSON: {exc}") from exc
    elif header == "DENIED":
        raise CredentialBrokerError(f"broker denied: {body.strip() or 'no reason given'}")
    elif header == "ERROR":
        raise CredentialBrokerError(f"broker error: {body.strip() or 'no detail'}")
    else:
        raise CredentialBrokerError(f"broker returned unknown status: {header!r}")


def get_cached(plugin_id: str | None = None) -> dict[str, Any]:
    """Return the credentials dict for this caller.

    Dispatch:
      1. If an in-process resolver is registered (API context), call it.
         No caching here — the resolver is expected to be cheap.
      2. Otherwise (subprocess context), do the one-shot broker fetch
         and cache for this subprocess's lifetime.

    For the resolver path, plugin_id is required. Callers like
    `get_credential(plugin_id, key)` pass it explicitly. `get_pg_conn()`
    doesn't need plugin-specific data — only the `__db__` block — so we
    resolve with a sentinel "__core__" id for the DB password lookup;
    the resolver should treat this as "give me __db__ only".

    Plugin authors never call this directly.
    """
    global _CACHE

    # Path 1: API process resolver
    if _RESOLVER is not None:
        pid = plugin_id or os.environ.get("NOUSVIZ_PLUGIN_ID", "").strip()
        if not pid:
            # No plugin_id — caller is asking for `__db__` only (e.g.
            # get_pg_conn from inside a plugin route). Use a sentinel.
            pid = "__core__"
        return _RESOLVER(pid)

    # Path 2: subprocess broker (cached per-process)
    if _CACHE is None:
        _CACHE = _fetch_once()
    return _CACHE


def reset_cache_for_tests() -> None:
    """Test-only: clear the cache so a subsequent call triggers a fresh
    fetch. Production code never calls this."""
    global _CACHE
    _CACHE = None
