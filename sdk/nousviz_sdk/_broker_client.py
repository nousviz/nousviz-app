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

# B341: a fetch that failed after the request was sent. The token is
# single-use, so dialling again can only be DENIED and would hide the real
# error; later calls re-raise this one instead.
_FAILURE: Exception | None = None

# B341: the broker sends every credential of the plugin in one reply. Read
# it all (up to this ceiling) and allow time for the broker to decrypt a
# large set before the first byte arrives.
MAX_REPLY_BYTES = 16 * 1024 * 1024
CONNECT_TIMEOUT_SECONDS = 5.0
REPLY_TIMEOUT_SECONDS = 60.0

# Resolver registry — the API process registers an in-process resolver
# at startup. Signature: resolver(plugin_id) -> dict[str, Any] including
# decrypted credentials and (optionally) the special "__db__" key.
# When None (default), subprocess broker path is used.
_RESOLVER: Optional[Callable[[str], dict[str, Any]]] = None

# Writer registry (B308) — the API process registers an in-process
# credential *writer* at startup, the symmetric counterpart to the
# resolver above. Signature: writer(plugin_id, field_name, plaintext,
# credential_type) -> None. Encrypts + persists via core's privileged
# store_plugin_credential. When None (default — e.g. subprocess context),
# credential writes are unsupported and store() raises.
_WRITER: Optional[Callable[[str, str, str, str], None]] = None


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


def register_writer(writer: Callable[[str, str, str, str], None]) -> None:
    """Register an in-process credential writer (B308).

    Used by the NousViz API process at startup so plugin route handlers
    can persist an encrypted credential they captured themselves (e.g. an
    OAuth access/refresh token exchanged in-route, where the provider
    can't redirect through core's callback). The writer encrypts + stores
    via core's privileged path; the credential never lands anywhere the
    ``nousviz_plugin`` role can read raw.

    Signature: ``writer(plugin_id, field_name, plaintext, credential_type)``.

    Plugin authors should NOT call this. Subprocess contexts don't register
    a writer, so :func:`store` raises there — credential writes are only
    supported from plugin route handlers (api-process context).
    """
    global _WRITER
    _WRITER = writer


def store(plugin_id: str, field_name: str, plaintext: str, credential_type: str) -> None:
    """Persist a credential via the registered in-process writer (B308).

    Only supported in api-process (plugin route) context. Raises
    :class:`CredentialBrokerUnavailable` in subprocess context, where no
    writer is registered — sync scripts read credentials, they don't mint
    them.
    """
    if _WRITER is None:
        raise CredentialBrokerUnavailable(
            "Credential writes are only supported from plugin route handlers "
            "(api-process context). No in-process credential writer is "
            "registered here — this usually means the call is happening in a "
            "worker-spawned subprocess (sync script / hook), which can read "
            "credentials but not store them."
        )
    _WRITER(plugin_id, field_name, plaintext, credential_type)


def reset_resolver_for_tests() -> None:
    """Test-only: unregister any resolver."""
    global _RESOLVER
    _RESOLVER = None


def reset_writer_for_tests() -> None:
    """Test-only: unregister any writer."""
    global _WRITER
    _WRITER = None


class CredentialBrokerUnavailable(RuntimeError):
    """Raised when the broker socket is not reachable. Typically means
    the plugin is running outside a NousViz-spawned subprocess."""


class CredentialBrokerError(RuntimeError):
    """Raised when the broker returns DENIED or ERROR."""


def _socket_recv_all(conn: socket.socket, max_bytes: int | None = None) -> bytes:
    """Read until EOF. The broker closes the connection after sending the
    response. A reply over `max_bytes` (MAX_REPLY_BYTES) is an error rather
    than a silently truncated read (B341: it used to stop at 64 KiB)."""
    limit = MAX_REPLY_BYTES if max_bytes is None else max_bytes
    parts: list[bytes] = []
    size = 0
    while True:
        chunk = conn.recv(65536)
        if not chunk:
            break
        size += len(chunk)
        if size > limit:
            raise CredentialBrokerError(
                f"broker reply is larger than {limit:,} bytes (read {size:,} so far); "
                f"raise MAX_REPLY_BYTES if this plugin really stores that many credentials"
            )
        parts.append(chunk)
    return b"".join(parts)


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
    sock.settimeout(CONNECT_TIMEOUT_SECONDS)
    try:
        try:
            sock.connect(socket_path)
        except (FileNotFoundError, ConnectionRefusedError) as exc:
            raise CredentialBrokerUnavailable(
                f"Cannot reach credential broker at {socket_path}: {exc}. "
                f"Is the NousViz jobs-worker running?"
            ) from exc

        request = f"AUTH {token}\nPLUGIN {plugin_id}\nGET\n".encode("ascii")
        # From here the token is spent: failures are CredentialBrokerError.
        try:
            sock.sendall(request)
            # The broker decrypts every credential before it answers.
            sock.settimeout(REPLY_TIMEOUT_SECONDS)
            response = _socket_recv_all(sock)
        except OSError as exc:  # includes socket.timeout
            raise CredentialBrokerError(f"broker exchange failed: {type(exc).__name__}: {exc}") from exc
        text = response.decode("ascii", errors="replace")
    finally:
        sock.close()

    # Every reply ends in a newline; without it the reply was cut short.
    if not text.endswith("\n"):
        raise CredentialBrokerError(
            f"incomplete reply from the broker ({len(response):,} bytes, no final newline)"
        )

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
    global _CACHE, _FAILURE

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
        if _FAILURE is not None:
            raise _FAILURE
        try:
            _CACHE = _fetch_once()
        except CredentialBrokerError as exc:
            # The token was sent and is now spent (B341): keep the real error.
            _FAILURE = exc
            raise
    return _CACHE


def reset_cache_for_tests() -> None:
    """Test-only: clear the cache so a subsequent call triggers a fresh
    fetch. Production code never calls this."""
    global _CACHE, _FAILURE
    _CACHE = None
    _FAILURE = None
