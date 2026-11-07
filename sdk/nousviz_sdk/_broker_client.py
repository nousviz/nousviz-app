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

import inspect
import json
import logging
import os
import socket
import stat
import threading
from typing import Any, Callable, Iterable, Optional

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

# B342: the cache may hold only the keys asked for so far. _FULL is True
# once it holds every credential of the plugin; _MISSING remembers keys the
# broker said are not stored, so they are not asked for again.
_FULL = False
_MISSING: set[str] = set()
_LOCK = threading.Lock()   # sync scripts call get_credential from several threads

# B342: the token arrives on a pipe (NOUSVIZ_CREDS_TOKEN_FD), not in the
# environment. It is read once, kept here, and the descriptor closed.
_TOKEN: Optional[str] = None
_TOKEN_ERROR: Optional[Exception] = None

# B341: the broker sends every credential of the plugin in one reply. Read
# it all (up to this ceiling) and allow time for the broker to decrypt a
# large set before the first byte arrives.
MAX_REPLY_BYTES = 16 * 1024 * 1024
CONNECT_TIMEOUT_SECONDS = 5.0
REPLY_TIMEOUT_SECONDS = 60.0

# Resolver registry — the API process registers an in-process resolver
# at startup. Signature: resolver(plugin_id, keys=None) -> dict[str, Any] including
# decrypted credentials and (optionally) the special "__db__" key.
# When None (default), subprocess broker path is used.
_RESOLVER: Optional[Callable[..., dict[str, Any]]] = None
# B342: resolvers may take (plugin_id, keys); older ones take plugin_id only.
_RESOLVER_TAKES_KEYS = False

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
    global _RESOLVER, _RESOLVER_TAKES_KEYS
    _RESOLVER = resolver
    try:
        params = inspect.signature(resolver).parameters.values()
        _RESOLVER_TAKES_KEYS = len([p for p in params if p.kind in (
            p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]) >= 2 or any(
            p.kind == p.VAR_POSITIONAL for p in params)
    except (TypeError, ValueError):
        _RESOLVER_TAKES_KEYS = False


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


class CredentialBrokerDenied(CredentialBrokerError):
    """The broker refused the token (B342: run released or expired, plugin
    mismatch, or a pre-B342 single-use token already spent)."""


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


def _read_token() -> Optional[str]:
    """The broker token for this process (B342).

    From the pipe named by NOUSVIZ_CREDS_TOKEN_FD: checked to be a pipe,
    read to EOF once, closed, and the variable removed so a child process
    doesn't inherit a stale descriptor number. Falls back to
    NOUSVIZ_CREDS_TOKEN (tests, workers from before B342)."""
    global _TOKEN, _TOKEN_ERROR
    if _TOKEN is not None:
        return _TOKEN
    if _TOKEN_ERROR is not None:
        raise _TOKEN_ERROR
    fd_text = os.environ.pop("NOUSVIZ_CREDS_TOKEN_FD", None)
    if fd_text is not None:
        try:
            fd = int(fd_text)
            if not stat.S_ISFIFO(os.fstat(fd).st_mode):
                raise CredentialBrokerUnavailable(
                    f"NOUSVIZ_CREDS_TOKEN_FD={fd_text} is not a pipe; refusing to read it")
            chunks = []
            while True:
                chunk = os.read(fd, 4096)
                if not chunk:
                    break
                chunks.append(chunk)
            os.close(fd)
            token = b"".join(chunks).decode("ascii", errors="replace").strip()
            if not token:
                raise CredentialBrokerError(
                    "the broker token pipe was empty (already read by another process?)")
        except CredentialBrokerError as exc:
            _TOKEN_ERROR = exc
            raise
        except (ValueError, OSError) as exc:
            _TOKEN_ERROR = CredentialBrokerUnavailable(
                f"could not read the broker token from NOUSVIZ_CREDS_TOKEN_FD={fd_text}: {exc}")
            raise _TOKEN_ERROR from exc
        _TOKEN = token
        return _TOKEN
    return os.environ.get("NOUSVIZ_CREDS_TOKEN") or None


def _per_key_mode() -> bool:
    """B342: the worker runs this sync with a run-scoped token
    (`sync.credential_fetch: per_key`). Otherwise the token is single-use
    and the SDK fetches the full set once."""
    return os.environ.get("NOUSVIZ_CREDS_MODE", "").strip() == "per_key"


def _fetch_once(keys: Optional[list[str]] = None) -> dict[str, Any]:
    """Open socket, authenticate, receive credentials JSON, return dict.

    With `keys` (B342), asks the broker for only those credentials (plus
    `__db__`); without, for every credential of the plugin.

    Raises CredentialBrokerUnavailable if socket/token env missing.
    Raises CredentialBrokerError if broker responds DENIED / ERROR.
    """
    socket_path = os.environ.get("NOUSVIZ_CREDS_SOCKET")
    plugin_id = os.environ.get("NOUSVIZ_PLUGIN_ID")
    token = _read_token() if socket_path and plugin_id else None

    if not socket_path or not token or not plugin_id:
        raise CredentialBrokerUnavailable(
            "NOUSVIZ_CREDS_SOCKET / NOUSVIZ_CREDS_TOKEN(_FD) / NOUSVIZ_PLUGIN_ID "
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

        keys_line = f"KEYS {json.dumps(keys)}\n" if keys is not None else ""
        request = f"AUTH {token}\nPLUGIN {plugin_id}\n{keys_line}GET\n".encode("ascii")
        try:
            sock.sendall(request)
            # The broker decrypts before it answers.
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
        raise CredentialBrokerDenied(f"broker denied: {body.strip() or 'no reason given'}")
    elif header == "ERROR":
        raise CredentialBrokerError(f"broker error: {body.strip() or 'no detail'}")
    else:
        raise CredentialBrokerError(f"broker returned unknown status: {header!r}")


def _call_resolver(pid: str, keys: Optional[list[str]]) -> dict[str, Any]:
    """Call the registered resolver with the keys asked for. A resolver
    registered before B342 takes only plugin_id; its full answer is then
    narrowed to `keys` here."""
    assert _RESOLVER is not None
    if _RESOLVER_TAKES_KEYS:
        return _RESOLVER(pid, keys)
    full = _RESOLVER(pid)
    if keys is None or not isinstance(full, dict):
        return full
    out = {k: full[k] for k in keys if k in full}
    if "__db__" in full:
        out["__db__"] = full["__db__"]
    return out


def get_cached(plugin_id: str | None = None, keys: Optional[Iterable[str]] = None) -> dict[str, Any]:
    """Return credentials for this caller: those named in `keys` (B342),
    or every credential of the plugin when `keys` is None. Always includes
    `__db__` when the source provides it.

    Dispatch:
      1. If an in-process resolver is registered (API context), call it
         with the keys. No caching here; reads are scoped and cheap.
      2. Otherwise (subprocess context), ask the broker for the keys not
         already fetched this run and cache the answers (including "not
         stored") for the subprocess's lifetime. The broker token is valid
         for the whole run, so keys can be fetched when they are needed.

    For the resolver path, plugin_id is required. Callers like
    `get_credential(plugin_id, key)` pass it explicitly. `get_pg_conn()`
    only needs `__db__`, so it asks with `keys=[]`; without a plugin id we
    resolve with the sentinel "__core__" ("give me __db__ only").

    Plugin authors never call this directly.
    """
    global _CACHE, _FAILURE, _FULL

    wanted: Optional[list[str]] = None if keys is None else [str(k) for k in keys]

    # Path 1: API process resolver
    if _RESOLVER is not None:
        pid = plugin_id or os.environ.get("NOUSVIZ_PLUGIN_ID", "").strip()
        if not pid:
            # No plugin_id — caller is asking for `__db__` only (e.g.
            # get_pg_conn from inside a plugin route). Use a sentinel.
            pid = "__core__"
        return _call_resolver(pid, wanted)

    # Path 2: subprocess broker (cached per-process)
    with _LOCK:
        if _FAILURE is not None:
            raise _FAILURE
        cache = _CACHE if _CACHE is not None else {}
        try:
            if wanted is None or not _per_key_mode():
                # Full set: asked for, or a single-use token (startup mode),
                # which allows one request only.
                if not _FULL:
                    cache.update(_fetch_once())
                    cache.pop("__scope__", None)
                    _FULL = True
            else:
                missing = [] if _FULL else sorted(
                    {k for k in wanted if k not in cache and k not in _MISSING})
                if missing or "__db__" not in cache:
                    try:
                        got = _fetch_once(missing)
                    except CredentialBrokerError as exc:
                        if "missing GET" not in str(exc):
                            raise
                        # A broker from before B342 does not know KEYS (and
                        # did not use the token): fall back to the full set.
                        got = _fetch_once()
                    if got.pop("__scope__", None) != "keys":
                        _FULL = True      # the broker sent everything (pre-B342 broker)
                    cache.update(got)
                    if not _FULL:
                        _MISSING.update(k for k in missing if k not in got)
        except CredentialBrokerError as exc:
            # A single-use token (startup mode) is spent by any request the
            # broker answered, and DENIED means the token is no longer valid
            # in either mode: asking again can only be denied, so keep the
            # real error (B341). A per-key token survives other errors.
            if isinstance(exc, CredentialBrokerDenied) or not _per_key_mode():
                _FAILURE = exc
            raise
        _CACHE = cache
        if wanted is None:
            return _CACHE
        out = {k: cache[k] for k in wanted if k in cache}
        if "__db__" in cache:
            out["__db__"] = cache["__db__"]
        return out


def reset_cache_for_tests() -> None:
    """Test-only: clear the cache so a subsequent call triggers a fresh
    fetch. Production code never calls this."""
    global _CACHE, _FAILURE, _FULL, _TOKEN, _TOKEN_ERROR
    _CACHE = None
    _FAILURE = None
    _FULL = False
    _MISSING.clear()
    _TOKEN = None
    _TOKEN_ERROR = None


# B342: read the token as soon as the SDK is imported in a spawned
# subprocess, so the pipe is emptied and closed before plugin code (or
# anything it starts) runs. Errors are kept and raised at first use.
if os.environ.get("NOUSVIZ_CREDS_TOKEN_FD"):
    try:
        _read_token()
    except Exception:  # noqa: BLE001 — surfaced at the first credential call
        pass
