"""
B342 (v1.0.8): scoped credential reads and usage telemetry.

No database: `get_pg_conn` is replaced by an in-memory fake that serves the
credentials table and records every statement, and decryption is counted.
The broker tests use a real broker on a temp socket with a stub decrypt.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ── In-memory credentials table ──────────────────────────────────────


class _Cursor:
    def __init__(self, db):
        self.db = db
        self._rows = []

    def execute(self, sql, params=None):
        self.db.statements.append((" ".join(sql.split()), params))
        if self.db.fail_on and self.db.fail_on in sql:
            raise RuntimeError("simulated failure")
        if "FROM credentials c" in sql:
            conn_name = params[0]
            names = set(params[1]) if len(params) > 1 else None
            self._rows = [
                (cid, name, b"enc-" + val.encode(), b"nonce", "conn-1")
                for cid, (name, val) in self.db.creds.items()
                if conn_name == "plugin:big-plugin" and (names is None or name in names)
            ]
        elif "SELECT id FROM connections" in sql:
            self._rows = [("conn-1",)] if params[0] == "plugin:big-plugin" else []
        else:
            self._rows = []

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None


class _FakeDb:
    def __init__(self, n: int):
        self.creds = {f"id-{i:05d}": (f"password:acct-{i:05d}", f"pw-{i}") for i in range(n)}
        self.statements: list = []
        self.fail_on: str | None = None

    @contextmanager
    def conn(self):
        class _C:
            def __init__(s):
                s.cur = _Cursor(self)

            def cursor(s):
                return s.cur
        yield _C()

    def sql(self, fragment):
        return [(s, p) for s, p in self.statements if fragment in s]


@pytest.fixture
def db(monkeypatch):
    import apps.api.src.credential_usage as cu
    import apps.api.src.plugin_credentials as pc

    fake = _FakeDb(5_000)
    monkeypatch.setattr(pc, "get_pg_conn", fake.conn)
    monkeypatch.setattr(cu, "get_pg_conn", fake.conn)
    decrypts = {"n": 0}

    def _decrypt(value, nonce):
        decrypts["n"] += 1
        if value == b"enc-BROKEN":
            raise ValueError("bad tag")
        return value.decode()[len("enc-"):]

    monkeypatch.setattr(pc, "_decrypt", _decrypt)
    fake.decrypts = decrypts
    return fake


# ── API reads ─────────────────────────────────────────────────────────


def test_one_key_reads_and_decrypts_one_credential(db):
    from apps.api.src.plugin_credentials import read_plugin_credentials

    out = read_plugin_credentials("big-plugin", ["password:acct-01234"], accessor="api:big-plugin")
    assert out == {"password:acct-01234": "pw-1234"}
    assert db.decrypts["n"] == 1
    select = db.sql("FROM credentials c")[0]
    assert "c.name = ANY(%s)" in select[0] and select[1][1] == ["password:acct-01234"]


def test_several_keys_one_query(db):
    from apps.api.src.plugin_credentials import read_plugin_credentials

    keys = ["password:acct-00001", "password:acct-00002", "password:nobody"]
    out = read_plugin_credentials("big-plugin", keys, accessor="api:big-plugin")
    assert out == {"password:acct-00001": "pw-1", "password:acct-00002": "pw-2"}
    assert len(db.sql("FROM credentials c")) == 1
    assert db.decrypts["n"] == 2


def test_empty_key_list_reads_nothing(db):
    from apps.api.src.plugin_credentials import read_plugin_credentials

    assert read_plugin_credentials("big-plugin", [], accessor="api:big-plugin") == {}
    assert db.statements == []


def test_reads_write_usage_not_a_row_per_credential(db):
    from apps.api.src.plugin_credentials import read_plugin_credentials

    out = read_plugin_credentials("big-plugin", None, accessor="broker:big-plugin",
                                  last_used_by="broker:big-plugin:run=7", fetch_detail="broker run=7")
    assert len(out) == 5_000
    # One throttled last_used update and one daily upsert, each for all 5,000 ids at once
    upd = db.sql("UPDATE credentials")
    ups = db.sql("INSERT INTO credential_usage_daily")
    assert len(upd) == 1 and len(ups) == 1
    assert "make_interval(secs => %s)" in upd[0][0]
    assert upd[0][1][0] == "broker:big-plugin:run=7" and len(upd[0][1][1]) == 5_000
    assert "ON CONFLICT (credential_id, day, accessor)" in ups[0][0] and ups[0][1][0] == "broker:big-plugin"
    assert ups[0][1][1] == sorted(ups[0][1][1])      # same lock order for concurrent reads
    # Exactly one audit row: the fetch
    audits = db.sql("INSERT INTO credential_audit_log")
    assert len(audits) == 1
    _, (cred_id, conn_id, action, by, detail) = audits[0]
    assert (cred_id, conn_id, action, by) == (None, "conn-1", "fetch", "broker:big-plugin:run=7")
    assert "scope=full" in detail and "returned=5000" in detail


def test_api_single_reads_write_no_audit_rows(db):
    from apps.api.src.plugin_credentials import read_plugin_credentials

    for _ in range(50):
        read_plugin_credentials("big-plugin", ["password:acct-00007"], accessor="api:big-plugin")
    assert db.sql("INSERT INTO credential_audit_log") == []
    assert len(db.sql("INSERT INTO credential_usage_daily")) == 50   # counted, one row per day in the DB


def test_decrypt_failure_is_an_event_and_the_rest_are_returned(db):
    from apps.api.src.plugin_credentials import read_plugin_credentials

    db.creds["id-broken"] = ("password:broken", "BROKEN")
    out = read_plugin_credentials("big-plugin", ["password:broken", "password:acct-00003"],
                                  accessor="api:big-plugin")
    assert out == {"password:acct-00003": "pw-3"}
    audits = db.sql("INSERT INTO credential_audit_log")
    assert len(audits) == 1 and audits[0][1][0] == "id-broken" and audits[0][1][2] == "decrypt_failed"


def test_telemetry_failure_does_not_fail_the_read(db, caplog):
    from apps.api.src.plugin_credentials import read_plugin_credentials

    db.fail_on = "credential_usage_daily"
    with caplog.at_level(logging.WARNING, logger="nousviz.credential_usage"):
        out = read_plugin_credentials("big-plugin", ["password:acct-00009"], accessor="api:big-plugin")
    assert out == {"password:acct-00009": "pw-9"}
    warnings = [r for r in caplog.records if "telemetry failed" in r.getMessage()]
    assert len(warnings) == 1


def test_get_plugin_credential_still_works_and_counts_usage(db):
    from apps.api.src.plugin_credentials import get_plugin_credential

    assert get_plugin_credential("big-plugin", "password:acct-00005", performed_by="settings_read") == "pw-5"
    assert db.decrypts["n"] == 1
    assert db.sql("INSERT INTO credential_usage_daily")[0][1][0] == "settings_read"
    assert db.sql("INSERT INTO credential_audit_log") == []


# ── SDK in the API process (resolver) ────────────────────────────────


def test_sdk_get_credential_and_get_credentials_via_resolver(db):
    from apps.api.src.plugin_credentials import read_plugin_credentials
    from sdk.nousviz_sdk import get_credential, get_credentials
    from sdk.nousviz_sdk import _broker_client as bc

    calls = []

    def resolver(plugin_id, keys=None):
        calls.append(keys)
        out = read_plugin_credentials(plugin_id, keys, accessor=f"api:{plugin_id}")
        out["__db__"] = {"user": "u", "password": "p"}
        return out

    bc.reset_resolver_for_tests()
    bc.register_resolver(resolver)
    try:
        assert get_credential("big-plugin", "password:acct-00011") == "pw-11"
        got = get_credentials("big-plugin", ["password:acct-00012", "password:none"])
        assert got == {"password:acct-00012": "pw-12", "password:none": None}
        assert calls == [["password:acct-00011"], ["password:acct-00012", "password:none"]]
        assert db.decrypts["n"] == 2
    finally:
        bc.reset_resolver_for_tests()


def test_pre_b342_one_argument_resolver_still_works():
    from sdk.nousviz_sdk import get_credential, get_credentials
    from sdk.nousviz_sdk import _broker_client as bc

    bc.reset_resolver_for_tests()
    bc.register_resolver(lambda plugin_id: {"a": "1", "b": "2", "__db__": {"user": "u"}})
    try:
        assert get_credential("p", "a") == "1"
        assert get_credentials("p", ["b", "zz"]) == {"b": "2", "zz": None}
        assert bc.get_cached("p", keys=["a"]) == {"a": "1", "__db__": {"user": "u"}}
    finally:
        bc.reset_resolver_for_tests()


# ── Broker v2 and the SDK in a subprocess ────────────────────────────


@pytest.fixture
def broker(monkeypatch):
    from apps.worker.src import credential_broker as cb
    import apps.api.src.plugin_credentials as real_plugin_creds

    stored = {f"password:acct-{i}": f"pw-{i}" for i in range(50)}
    stored["sdi_token"] = "tok"
    calls: list = []

    def fake_list(plugin_id, keys=None, **kw):
        calls.append((plugin_id, None if keys is None else list(keys), kw))
        if keys is None:
            return dict(stored)
        return {k: stored[k] for k in keys if k in stored}

    monkeypatch.setattr(real_plugin_creds, "list_plugin_credentials_decrypted", fake_list, raising=False)
    monkeypatch.setenv("NOUSVIZ_PLUGIN_USER", "nousviz_plugin")
    monkeypatch.setenv("NOUSVIZ_PLUGIN_PASSWORD", "db-pw")
    d = tempfile.mkdtemp(prefix="nv_", dir="/tmp")
    os.chmod(d, 0o700)
    path = str(Path(d) / "c.sock")
    b = cb.CredentialBroker(socket_path=path)
    b.start()
    time.sleep(0.05)
    yield b, path, calls
    b.stop()
    import shutil
    shutil.rmtree(d, ignore_errors=True)


def _raw(path, token, plugin, keys=None):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect(path)
    line = f"KEYS {json.dumps(keys)}\n" if keys is not None else ""
    s.sendall(f"AUTH {token}\nPLUGIN {plugin}\n{line}GET\n".encode())
    buf = b""
    while True:
        c = s.recv(65536)
        if not c:
            break
        buf += c
    s.close()
    return buf.decode()


def test_broker_keys_returns_only_those(broker):
    b, path, calls = broker
    t = b.register_spawn("big-plugin", 9)
    resp = _raw(path, t, "big-plugin", ["password:acct-3", "password:nope"])
    data = json.loads(resp[3:])
    assert set(data) == {"password:acct-3", "__db__", "__scope__"} and data["__scope__"] == "keys"
    plugin, keys, kw = calls[-1]
    assert keys == ["password:acct-3", "password:nope"]
    assert kw["accessor"] == "broker:big-plugin" and kw["last_used_by"] == "broker:big-plugin:run=9"
    assert kw["fetch_detail"] == "broker run=9"


def test_broker_without_keys_is_the_full_set(broker):
    b, path, calls = broker
    t = b.register_spawn("big-plugin", 9)
    data = json.loads(_raw(path, t, "big-plugin")[3:])
    assert data["__scope__"] == "full" and len(data) == 51 + 2


def test_broker_mismatch_burns_and_records_denied(broker, monkeypatch):
    from apps.worker.src import credential_broker as cb

    b, path, _ = broker
    denied = []
    monkeypatch.setattr(cb.CredentialBroker, "_record_denied", staticmethod(lambda s, r: denied.append((s.plugin_id, r))))
    t = b.register_spawn("big-plugin", 9)
    assert _raw(path, t, "other-plugin", ["password:acct-1"]).startswith("DENIED")
    assert _raw(path, t, "big-plugin", ["password:acct-1"]).startswith("DENIED")
    assert denied == [("big-plugin", "other-plugin")]


@pytest.mark.parametrize("bad", ['KEYS not-json', 'KEYS {"a": 1}', 'KEYS ["ok", 3]', 'KEYS [""]'])
def test_broker_rejects_malformed_keys(bad):
    from apps.worker.src.credential_broker import CredentialBroker, _BadRequest

    with pytest.raises(_BadRequest):
        CredentialBroker._parse_request(f"AUTH t\nPLUGIN p\n{bad}\nGET\n".encode())


def test_broker_request_size_cap(broker):
    from apps.worker.src.credential_broker import MAX_REQUEST_BYTES

    b, path, _ = broker
    t = b.register_spawn("big-plugin", 9)
    keys = [f"k{i:06d}" for i in range(MAX_REQUEST_BYTES // 8)]
    # Refused: an ERROR reply, or the broker closes while we are still sending.
    try:
        resp = _raw(path, t, "big-plugin", keys)
    except (ConnectionResetError, BrokenPipeError):
        resp = "ERROR (connection closed)"
    assert resp.startswith("ERROR")
    # The token still works for a normal request.
    assert _raw(path, t, "big-plugin", ["password:acct-1"]).startswith("OK")


def _sdk_env(monkeypatch, path, token, plugin="big-plugin"):
    from sdk.nousviz_sdk import _broker_client as bc

    bc.reset_resolver_for_tests()
    bc.reset_cache_for_tests()
    monkeypatch.setenv("NOUSVIZ_CREDS_SOCKET", path)
    monkeypatch.setenv("NOUSVIZ_CREDS_TOKEN", token)
    monkeypatch.setenv("NOUSVIZ_PLUGIN_ID", plugin)
    monkeypatch.setenv("NOUSVIZ_CREDS_MODE", "per_key")
    monkeypatch.delenv("NOUSVIZ_CREDS_TOKEN_FD", raising=False)
    return bc


def test_sdk_fetches_each_key_when_needed_and_caches(broker, monkeypatch):
    from sdk.nousviz_sdk import get_credential, get_credentials

    b, path, calls = broker
    bc = _sdk_env(monkeypatch, path, b.register_spawn("big-plugin", 9, per_key=True))
    try:
        assert get_credential("big-plugin", "password:acct-1") == "pw-1"
        assert get_credential("big-plugin", "password:acct-1") == "pw-1"          # cached
        assert get_credential("big-plugin", "password:missing") is None
        assert get_credential("big-plugin", "password:missing") is None           # "not stored" cached
        got = get_credentials("big-plugin", ["password:acct-2", "password:acct-3", "password:acct-1"])
        assert got == {"password:acct-2": "pw-2", "password:acct-3": "pw-3", "password:acct-1": "pw-1"}
        asked = [k for _, k, _ in calls]
        assert asked == [["password:acct-1"], ["password:missing"], ["password:acct-2", "password:acct-3"]]
        # get_pg_conn's __db__ comes from the cache: no further request
        assert bc.get_cached(keys=[])["__db__"]["password"] == "db-pw"
        assert len(calls) == 3
    finally:
        bc.reset_cache_for_tests()


def test_sdk_after_run_released_is_denied_once(broker, monkeypatch):
    from sdk.nousviz_sdk import get_credential

    b, path, calls = broker
    bc = _sdk_env(monkeypatch, path, b.register_spawn("big-plugin", 9, per_key=True))
    try:
        assert get_credential("big-plugin", "password:acct-1") == "pw-1"
        b.release_run(9)
        with pytest.raises(bc.CredentialBrokerDenied):
            get_credential("big-plugin", "password:acct-2")
        with pytest.raises(bc.CredentialBrokerDenied):
            get_credential("big-plugin", "password:acct-4")
        assert len(calls) == 1      # the second refusal did not dial again
    finally:
        bc.reset_cache_for_tests()


def test_sdk_falls_back_to_full_fetch_with_a_pre_b342_broker(monkeypatch):
    """A broker from before B342 answers a KEYS request with ERROR "missing
    GET" without using the token, then serves the full set once."""
    import threading

    d = tempfile.mkdtemp(prefix="nv_", dir="/tmp")
    path = str(Path(d) / "old.sock")
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    srv.listen(4)
    seen = []

    def serve():
        while True:
            try:
                c, _ = srv.accept()
            except OSError:
                return
            req = c.recv(4096).decode()
            seen.append(req)
            if "KEYS" in req:
                c.sendall(b"ERROR\nmissing GET\n")
            else:
                c.sendall(b'OK\n{"a": "1", "b": "2", "__db__": {"user": "u"}}\n')
            c.close()

    threading.Thread(target=serve, daemon=True).start()
    from sdk.nousviz_sdk import get_credential

    bc = _sdk_env(monkeypatch, path, "tok", plugin="p")
    try:
        assert get_credential("p", "a") == "1"
        assert get_credential("p", "b") == "2"
        assert len(seen) == 2       # KEYS refused, then one full fetch; "b" came from the cache
    finally:
        srv.close()
        bc.reset_cache_for_tests()


def test_get_pg_conn_asks_for_db_only(monkeypatch):
    from sdk.nousviz_sdk import _broker_client as bc

    seen = []
    bc.reset_resolver_for_tests()
    bc.register_resolver(lambda pid, keys=None: seen.append((pid, keys)) or {"__db__": {"user": "u", "password": ""}})
    import sdk.nousviz_sdk.db as sdb
    try:
        with pytest.raises(Exception):
            with sdb.get_pg_conn():
                pass
        assert seen and seen[0][1] == []
    finally:
        bc.reset_resolver_for_tests()


# ── Retention ────────────────────────────────────────────────────────


def test_retention_policies_cover_reads_and_keep_lifecycle():
    from apps.api.src.services.retention import POLICIES_BY_KEY

    reads = POLICIES_BY_KEY["credential_audit_log:reads"]
    assert reads.table == "credential_audit_log" and reads.default_days == 90
    assert reads.additional_where == "action IN ('fetch', 'used')"
    usage = POLICIES_BY_KEY["credential_usage_daily"]
    assert usage.table == "credential_usage_daily" and usage.field == "last_at" and usage.default_days == 400


# ── Addendum: opt-in run-scoped tokens, token on a pipe ──────────────


def test_startup_mode_is_one_full_fetch_with_a_single_use_token(broker, monkeypatch):
    from sdk.nousviz_sdk import get_credential, get_credentials

    b, path, calls = broker
    bc = _sdk_env(monkeypatch, path, b.register_spawn("big-plugin", 9))
    monkeypatch.setenv("NOUSVIZ_CREDS_MODE", "startup")
    try:
        assert get_credential("big-plugin", "password:acct-1") == "pw-1"
        assert get_credentials("big-plugin", ["password:acct-2", "sdi_token"]) == {
            "password:acct-2": "pw-2", "sdi_token": "tok"}
        assert get_credential("big-plugin", "password:none") is None
        assert [k for _, k, _ in calls] == [None]          # one full fetch
    finally:
        bc.reset_cache_for_tests()


def test_startup_mode_error_is_not_retried(monkeypatch):
    """A single-use token is spent by any answered request (B341 rule)."""
    import threading

    d = tempfile.mkdtemp(prefix="nv_", dir="/tmp")
    path = str(Path(d) / "e.sock")
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    srv.listen(4)
    seen = []

    def serve():
        while True:
            try:
                c, _ = srv.accept()
            except OSError:
                return
            seen.append(c.recv(4096))
            c.sendall(b"ERROR\ndb down\n")
            c.close()

    threading.Thread(target=serve, daemon=True).start()
    from sdk.nousviz_sdk import get_credential

    bc = _sdk_env(monkeypatch, path, "tok", plugin="p")
    monkeypatch.setenv("NOUSVIZ_CREDS_MODE", "startup")
    try:
        for _ in range(2):
            with pytest.raises(bc.CredentialBrokerError, match="db down"):
                get_credential("p", "a")
        assert len(seen) == 1
    finally:
        srv.close()
        bc.reset_cache_for_tests()


def test_worker_hands_the_token_over_on_a_pipe(monkeypatch):
    import stat as _stat
    from apps.worker.src import credential_broker as cb
    from apps.worker.src import run_jobs

    b = cb.CredentialBroker(socket_path="/tmp/unused.sock")
    monkeypatch.setattr(run_jobs, "_broker", b)
    for per_key, mode in ((False, "startup"), (True, "per_key")):
        env, fds = run_jobs._broker_handover("big-plugin", 5, per_key=per_key)
        try:
            assert "NOUSVIZ_CREDS_TOKEN" not in env
            assert env["NOUSVIZ_CREDS_MODE"] == mode and env["NOUSVIZ_CREDS_SOCKET"] == "/tmp/unused.sock"
            fd = int(env["NOUSVIZ_CREDS_TOKEN_FD"])
            assert fds == (fd,) and _stat.S_ISFIFO(os.fstat(fd).st_mode)
            token = os.read(fd, 4096).decode()
            spawn = b._pending[token]
            assert spawn.single_use is (not per_key) and spawn.run_id == 5
        finally:
            run_jobs._close_fds(fds)


def test_sdk_reads_the_pipe_once_and_forgets_it(monkeypatch):
    from sdk.nousviz_sdk import _broker_client as bc

    bc.reset_cache_for_tests()
    r, w = os.pipe()
    os.write(w, b"tok-from-pipe")
    os.close(w)
    monkeypatch.setenv("NOUSVIZ_CREDS_TOKEN_FD", str(r))
    monkeypatch.delenv("NOUSVIZ_CREDS_TOKEN", raising=False)
    try:
        assert bc._read_token() == "tok-from-pipe"
        assert "NOUSVIZ_CREDS_TOKEN_FD" not in os.environ
        with pytest.raises(OSError):
            os.fstat(r)                       # closed
        assert bc._read_token() == "tok-from-pipe"   # kept in memory
    finally:
        bc.reset_cache_for_tests()


def test_sdk_refuses_a_descriptor_that_is_not_a_pipe(monkeypatch, tmp_path):
    from sdk.nousviz_sdk import _broker_client as bc

    bc.reset_cache_for_tests()
    f = tmp_path / "not-a-pipe"
    f.write_text("secret-file-content")
    fd = os.open(f, os.O_RDONLY)
    monkeypatch.setenv("NOUSVIZ_CREDS_TOKEN_FD", str(fd))
    try:
        with pytest.raises(bc.CredentialBrokerUnavailable, match="not a pipe"):
            bc._read_token()
        assert os.lseek(fd, 0, os.SEEK_CUR) == 0       # nothing was read
    finally:
        os.close(fd)
        bc.reset_cache_for_tests()


def test_spawned_child_gets_the_token_and_its_own_child_does_not(tmp_path):
    """End to end with real processes: the sync (child) reads the token from
    the pipe at SDK import; a process it starts (grandchild) has neither the
    variable nor the descriptor."""
    import subprocess
    import textwrap

    child = tmp_path / "child.py"
    child.write_text(textwrap.dedent(f"""
        import os, subprocess, sys
        sys.path.insert(0, {str(REPO_ROOT)!r})
        fd = int(os.environ["NOUSVIZ_CREDS_TOKEN_FD"])
        import sdk.nousviz_sdk._broker_client as bc
        print("token=" + str(bc._TOKEN))
        print("env_after=" + str("NOUSVIZ_CREDS_TOKEN_FD" in os.environ))
        try:
            os.fstat(fd); print("fd_open=True")
        except OSError:
            print("fd_open=False")
        g = subprocess.run([sys.executable, "-c",
            "import os; print('grand_env=' + str(os.environ.get('NOUSVIZ_CREDS_TOKEN_FD'))); "
            "print('grand_token_env=' + str(os.environ.get('NOUSVIZ_CREDS_TOKEN')))"],
            capture_output=True, text=True)
        print(g.stdout.strip())
    """))
    r, w = os.pipe()
    os.write(w, b"tok-xyz")
    os.close(w)
    env = {"PATH": os.environ.get("PATH", ""), "NOUSVIZ_CREDS_TOKEN_FD": str(r),
           "NOUSVIZ_CREDS_SOCKET": "/tmp/none.sock", "NOUSVIZ_PLUGIN_ID": "p"}
    try:
        out = subprocess.run([sys.executable, str(child)], env=env, pass_fds=(r,),
                             capture_output=True, text=True, timeout=60)
    finally:
        os.close(r)
    lines = dict(line.split("=", 1) for line in out.stdout.split() if "=" in line)
    assert lines == {"token": "tok-xyz", "env_after": "False", "fd_open": "False",
                     "grand_env": "None", "grand_token_env": "None"}, out.stderr
