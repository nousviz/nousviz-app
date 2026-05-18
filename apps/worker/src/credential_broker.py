"""
Credential broker — Unix socket server running inside the jobs-worker.

Delivers decrypted credentials + low-privilege DB password to plugin
subprocesses WITHOUT those values ever entering subprocess `os.environ`.

## Protocol

The broker listens on a Unix domain socket. Each connection is a single
request/response exchange; the broker closes the socket after responding.

Request (newline-delimited text):
    AUTH <token>
    PLUGIN <plugin_id>
    GET

Response:
    OK
    <JSON object>

or

    DENIED
    <short reason>

or

    ERROR
    <short reason>

The JSON response contains decrypted credentials for the plugin plus a
special `__db__` key carrying the nousviz_plugin role's DB password:

    {
      "password": "...",
      "api_token": "...",
      "ssl_ca": "-----BEGIN CERTIFICATE-----\\n...",
      "__db__": {
        "user": "nousviz_plugin",
        "password": "..."
      }
    }

## Token lifecycle

The worker calls `register_spawn(plugin_id, run_id)` BEFORE it spawns a
subprocess; the broker generates a 32-byte random token, stores
`{token: (plugin_id, run_id, expires_at)}`, and returns the token. The
worker passes the token to the subprocess via `NOUSVIZ_CREDS_TOKEN`
(alongside `NOUSVIZ_CREDS_SOCKET` = the socket path).

The subprocess's SDK connects to the socket, sends `AUTH/PLUGIN/GET`,
and receives its credentials. The broker then **deletes** the token.

- Single-use: second attempt with the same token returns `DENIED`
- Time-bound: tokens expire 30s after registration
- Plugin-scoped: `PLUGIN <plugin_id>` must match what was registered;
  a token leaked to another plugin yields `DENIED`

## Security model

- Broker runs as the worker user; socket dir is mode 0700 (plugin
  subprocesses share UID, so they can connect).
- A compromised plugin exfiltrating its token gains nothing: the token
  is already consumed by the time the subprocess finishes its startup
  fetch.
- A compromised plugin trying to `AUTH <other_plugin_token> / PLUGIN other`
  is stopped by the plugin_id binding check.
- Broker holds decrypted values only in-memory during the handler;
  response is flushed and the connection is closed.

## Failure modes

Worker dies → broker dies → subprocess sees ECONNREFUSED → SDK raises.
Broker DB read fails → ERROR response → SDK raises.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import socket
import stat
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nousviz.broker")

TOKEN_TTL_SEC = 30
TOKEN_BYTES = 32


def _default_socket_path() -> str:
    """Resolve the default socket path.

    Priority:
      1. NOUSVIZ_CREDS_SOCKET env var (explicit override)
      2. <repo_root>/run/creds.sock — repo-root-relative, works on dev
         (repo anywhere on disk) and server (/opt/nousviz/run/creds.sock)
    """
    explicit = os.environ.get("NOUSVIZ_CREDS_SOCKET")
    if explicit:
        return explicit
    # This file lives at apps/worker/src/credential_broker.py, so go
    # up three to get the repo root.
    from pathlib import Path as _P
    repo_root = _P(__file__).resolve().parents[3]
    return str(repo_root / "run" / "creds.sock")


# Socket default resolved lazily at instantiation so tests can override
# NOUSVIZ_CREDS_SOCKET after import. Callers should prefer
# `CredentialBroker(socket_path=...)` explicitly.
DEFAULT_SOCKET_PATH = _default_socket_path()


@dataclass
class _PendingSpawn:
    plugin_id: str
    run_id: int | None
    expires_at: float


class CredentialBroker:
    """Thread-safe in-memory token registry + Unix socket server.

    Usage (inside the jobs-worker):
        broker = CredentialBroker(socket_path="/opt/nousviz/run/creds.sock")
        broker.start()

        # Before spawning a subprocess for sync/hook:
        token = broker.register_spawn(plugin_id, run_id)
        subprocess.Popen(..., env={"NOUSVIZ_CREDS_SOCKET": socket_path,
                                    "NOUSVIZ_CREDS_TOKEN": token,
                                    ...})

    The broker decrypts credentials on demand per request. It does NOT
    cache decrypted values across requests. The encryption key lives in
    the worker's own env (as today); it never enters a subprocess.
    """

    def __init__(self, socket_path: str = DEFAULT_SOCKET_PATH) -> None:
        self._socket_path = socket_path
        self._lock = threading.Lock()
        self._pending: dict[str, _PendingSpawn] = {}
        self._server: Optional[socket.socket] = None
        self._accept_thread: Optional[threading.Thread] = None
        self._sweeper_thread: Optional[threading.Thread] = None
        self._stopping = threading.Event()

    # ── Token registration (called by worker parent) ─────────────────

    def register_spawn(self, plugin_id: str, run_id: int | None = None) -> str:
        """Generate a one-shot token bound to (plugin_id, run_id). Call
        this RIGHT before `subprocess.Popen(...)`."""
        token = secrets.token_urlsafe(TOKEN_BYTES)
        with self._lock:
            self._pending[token] = _PendingSpawn(
                plugin_id=plugin_id,
                run_id=run_id,
                expires_at=time.time() + TOKEN_TTL_SEC,
            )
        return token

    # ── Lifecycle ────────────────────────────────────────────────────

    def start(self) -> None:
        """Bind the socket and start accept + sweeper threads."""
        sock_path = Path(self._socket_path)
        sock_path.parent.mkdir(parents=True, exist_ok=True)
        # Dir must be 0700 so other users can't connect to the socket.
        os.chmod(sock_path.parent, stat.S_IRWXU)

        # Remove stale socket from a previous run.
        if sock_path.exists():
            sock_path.unlink()

        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(str(sock_path))
        # Socket file itself must also be 0700 (owner only).
        os.chmod(sock_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        self._server.listen(8)
        self._server.settimeout(1.0)  # let the accept loop check _stopping

        self._accept_thread = threading.Thread(
            target=self._accept_loop, name="credential-broker", daemon=True
        )
        self._accept_thread.start()

        self._sweeper_thread = threading.Thread(
            target=self._sweep_loop, name="broker-token-sweeper", daemon=True
        )
        self._sweeper_thread.start()

        logger.info(f"credential broker listening on {sock_path}")

    def stop(self) -> None:
        """Signal threads to exit; close socket; remove socket file."""
        self._stopping.set()
        if self._server is not None:
            try:
                self._server.close()
            except Exception:
                pass
        try:
            Path(self._socket_path).unlink()
        except FileNotFoundError:
            pass
        except Exception as exc:
            logger.warning(f"broker socket cleanup failed: {exc}")

    # ── Internal: accept + handler ───────────────────────────────────

    def _accept_loop(self) -> None:
        assert self._server is not None
        while not self._stopping.is_set():
            try:
                conn, _ = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                # Socket closed during shutdown.
                break
            # Each request is tiny; run in a thread so one slow DB call
            # can't block other spawns.
            threading.Thread(
                target=self._handle, args=(conn,), daemon=True
            ).start()

    def _handle(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(5.0)
            data = self._recv_request(conn)
            token, plugin_id = self._parse_request(data)
            spawn = self._consume_token(token, plugin_id)
            if spawn is None:
                self._send(conn, "DENIED\ntoken invalid or expired or plugin mismatch\n")
                return
            try:
                creds = self._fetch_credentials(spawn.plugin_id)
            except Exception as exc:
                logger.error(
                    f"broker DB read failed for {spawn.plugin_id}: {exc}",
                    exc_info=True,
                )
                self._send(conn, f"ERROR\n{type(exc).__name__}: {str(exc)[:200]}\n")
                return
            payload = json.dumps(creds)
            self._send(conn, f"OK\n{payload}\n")
            logger.info(
                f"broker served credentials for plugin={spawn.plugin_id} "
                f"run={spawn.run_id} fields={len(creds) - 1}"  # minus __db__
            )
        except _BadRequest as exc:
            self._send(conn, f"ERROR\n{exc}\n")
        except Exception as exc:
            logger.error(
                f"broker handler crashed: {exc}\n{traceback.format_exc()}"
            )
            try:
                self._send(conn, f"ERROR\ninternal: {type(exc).__name__}\n")
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @staticmethod
    def _recv_request(conn: socket.socket) -> bytes:
        """Read up to 1 KiB of newline-delimited text. Refuses anything
        larger — the protocol is tiny and larger payloads indicate abuse."""
        buf = b""
        while b"GET\n" not in buf and len(buf) < 1024:
            chunk = conn.recv(256)
            if not chunk:
                break
            buf += chunk
        return buf

    @staticmethod
    def _parse_request(data: bytes) -> tuple[str, str]:
        """Parse `AUTH <token>\\nPLUGIN <plugin_id>\\nGET\\n`."""
        try:
            text = data.decode("ascii")
        except UnicodeDecodeError:
            raise _BadRequest("non-ascii payload")
        lines = [line for line in text.split("\n") if line]
        if len(lines) < 3:
            raise _BadRequest("short request")
        if not lines[0].startswith("AUTH "):
            raise _BadRequest("missing AUTH")
        if not lines[1].startswith("PLUGIN "):
            raise _BadRequest("missing PLUGIN")
        if lines[2] != "GET":
            raise _BadRequest("missing GET")
        token = lines[0][len("AUTH "):].strip()
        plugin_id = lines[1][len("PLUGIN "):].strip()
        if not token or not plugin_id:
            raise _BadRequest("empty field")
        return token, plugin_id

    def _consume_token(self, token: str, plugin_id: str) -> Optional[_PendingSpawn]:
        now = time.time()
        with self._lock:
            spawn = self._pending.pop(token, None)
        if spawn is None:
            return None
        if spawn.expires_at < now:
            return None
        if spawn.plugin_id != plugin_id:
            # Do NOT restore — consume even on mismatch. A plugin that
            # presents someone else's token forfeits it.
            logger.warning(
                f"broker: token plugin mismatch — token for {spawn.plugin_id}, "
                f"requested by {plugin_id}"
            )
            return None
        return spawn

    # ── Internal: DB read for credentials + DB password ──────────────

    def _fetch_credentials(self, plugin_id: str) -> dict:
        """Read and decrypt all credentials for this plugin, plus the
        low-privilege DB role password. Returns the JSON-serializable dict
        the subprocess expects.
        """
        from apps.api.src.plugin_credentials import list_plugin_credentials_decrypted

        creds = list_plugin_credentials_decrypted(plugin_id) or {}

        # Attach the nousviz_plugin DB password so the SDK's
        # get_pg_conn() never has to read it from env. The worker's
        # own .env provides NOUSVIZ_PLUGIN_PASSWORD — we pass it through.
        creds["__db__"] = {
            "user": os.environ.get("NOUSVIZ_PLUGIN_USER", "nousviz_plugin"),
            "password": os.environ.get("NOUSVIZ_PLUGIN_PASSWORD", ""),
        }
        return creds

    # ── Internal: expired-token sweeper ──────────────────────────────

    def _sweep_loop(self) -> None:
        while not self._stopping.is_set():
            time.sleep(60)
            cutoff = time.time()
            with self._lock:
                expired = [t for t, s in self._pending.items() if s.expires_at < cutoff]
                for t in expired:
                    del self._pending[t]
            if expired:
                logger.info(f"broker swept {len(expired)} expired tokens")

    @staticmethod
    def _send(conn: socket.socket, payload: str) -> None:
        try:
            conn.sendall(payload.encode("ascii"))
        except Exception:
            pass


class _BadRequest(Exception):
    pass
