"""B347 — inbound webhooks verify the timestamped signature (V2) and reject
replays.

`POST /api/webhooks/in/{slug}` rules when the endpoint has a secret:

  * X-Webhook-Timestamp + X-Webhook-Signature-V2 present -> verify V2 only:
    the timestamp must be within INBOUND_REPLAY_WINDOW_SECONDS of server time
    and the signature must equal HMAC-SHA256(secret, f"{ts}." + body).
    Any failure is 401; there is NO fallback to V1.
  * No V2 headers -> V1 (X-Webhook-Signature) as before, unless the endpoint
    has require_signature_v2, in which case 401.
  * The same verified V2 signature on the same endpoint within
    INBOUND_DUPLICATE_WINDOW_SECONDS -> 409, nothing stored.

The route runs against an in-memory stand-in for the two webhook tables, so
the test needs no database. The stand-in commits on success and discards
writes on an exception, like the SDK's `get_pg_conn()`.
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import sys
import time
import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from apps.api.src.services.webhook_dispatch import sign_headers  # noqa: E402

_ROUTES_PATH = REPO / "plugins" / "utilities" / "webhooks" / "api" / "routes.py"
_spec = importlib.util.spec_from_file_location("b347_webhooks_routes", _ROUTES_PATH)
routes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(routes)

SECRET = "b347-secret"
BODY = b'{"hello":"b347"}'


# ── In-memory stand-in for webhook_endpoints / webhook_events ────────

class FakeDB:
    def __init__(self):
        self.endpoints: dict[str, dict] = {}
        self.events: list[dict] = []

    def add_endpoint(self, *, secret=SECRET, require_v2=False, active=True) -> str:
        slug = uuid.uuid4().hex
        self.endpoints[slug] = {
            "id": str(uuid.uuid4()),
            "secret": secret,
            "is_active": active,
            "require_signature_v2": require_v2,
            "event_count": 0,
        }
        return slug

    def events_for(self, slug):
        eid = self.endpoints[slug]["id"]
        return [e for e in self.events if e["endpoint_id"] == eid]


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._rows: list = []

    def execute(self, sql, params=()):
        q = " ".join(sql.split())
        db = self.conn.db
        if q.startswith("SELECT id, secret, is_active, require_signature_v2 FROM webhook_endpoints WHERE slug = %s"):
            ep = db.endpoints.get(params[0])
            self._rows = [dict(ep)] if ep else []
        elif q == "SELECT 1 FROM webhook_endpoints WHERE id = %s FOR UPDATE":
            self._rows = [(1,)]
        elif q.startswith("SELECT 1 FROM webhook_events WHERE endpoint_id = %s AND received_at > now() - make_interval(secs => %s) AND headers->>'x-webhook-signature-v2' = %s"):
            eid, window, sig = params
            cutoff = time.time() - window
            self._rows = [
                (1,) for e in db.events + self.conn.pending
                if e["endpoint_id"] == eid
                and e["received_at"] > cutoff
                and e["headers"].get("x-webhook-signature-v2") == sig
            ][:1]
        elif q.startswith("INSERT INTO webhook_events"):
            eid, payload, headers, ip = params
            self.conn.pending.append({
                "endpoint_id": eid,
                "payload": json.loads(payload),
                "headers": json.loads(headers),
                "source_ip": ip,
                "received_at": time.time(),
            })
            self._rows = []
        elif q.startswith("UPDATE webhook_endpoints SET event_count = event_count + 1"):
            self._rows = []
        else:  # pragma: no cover - a new query needs a stand-in here
            raise AssertionError(f"unexpected SQL: {q}")

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakeConn:
    def __init__(self, db):
        self.db = db
        self.pending: list[dict] = []

    def cursor(self):
        return FakeCursor(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type is None:
            self.db.events.extend(self.pending)
        self.pending = []
        return False


@pytest.fixture
def db(monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(routes, "_get_conn", lambda: FakeConn(fake))
    monkeypatch.setattr(routes, "_dict_cursor", lambda conn: conn.cursor())
    return fake


@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(routes.ingestion_router, prefix="/api")
    return TestClient(app)


# ── Helpers ──────────────────────────────────────────────────────────

def v1(body=BODY, secret=SECRET):
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def v2(ts, body=BODY, secret=SECRET):
    return hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()


def v2_headers(ts=None, body=BODY, secret=SECRET):
    ts = int(time.time()) if ts is None else ts
    return {"X-Webhook-Timestamp": str(ts), "X-Webhook-Signature-V2": v2(ts, body, secret)}


def post(client, slug, headers, body=BODY):
    return client.post(
        f"/api/webhooks/in/{slug}",
        content=body,
        headers={"Content-Type": "application/json", **headers},
    )


# ── V2 verification ──────────────────────────────────────────────────

def test_valid_v2_now_is_accepted_and_stored(client, db):
    slug = db.add_endpoint()
    r = post(client, slug, v2_headers())
    assert r.status_code == 200
    events = db.events_for(slug)
    assert len(events) == 1
    assert events[0]["payload"] == {"hello": "b347"}
    # The V2 signature and timestamp are kept in the saved headers.
    assert "x-webhook-signature-v2" in events[0]["headers"]
    assert "x-webhook-timestamp" in events[0]["headers"]


@pytest.mark.parametrize("offset", [-301, 301])
def test_v2_outside_window_is_expired(client, db, offset):
    slug = db.add_endpoint()
    r = post(client, slug, v2_headers(int(time.time()) + offset))
    assert r.status_code == 401
    assert r.json()["detail"] == "Signature expired"
    assert db.events_for(slug) == []


@pytest.mark.parametrize("offset", [-299, 299])
def test_v2_just_inside_window_is_accepted(client, db, offset):
    slug = db.add_endpoint()
    assert post(client, slug, v2_headers(int(time.time()) + offset)).status_code == 200


def test_window_constant():
    assert routes.INBOUND_REPLAY_WINDOW_SECONDS == 300
    assert routes.INBOUND_DUPLICATE_WINDOW_SECONDS == 600


def test_stale_v2_with_valid_v1_does_not_fall_back(client, db):
    slug = db.add_endpoint()
    headers = {**v2_headers(int(time.time()) - 301), "X-Webhook-Signature": v1()}
    r = post(client, slug, headers)
    assert r.status_code == 401
    assert db.events_for(slug) == []


def test_bad_v2_with_valid_v1_does_not_fall_back(client, db):
    slug = db.add_endpoint()
    headers = {**v2_headers(), "X-Webhook-Signature": v1()}
    headers["X-Webhook-Signature-V2"] = "0" * 64
    r = post(client, slug, headers)
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid signature"


def test_wrong_v2_signature(client, db):
    slug = db.add_endpoint()
    headers = v2_headers(secret="some-other-secret")
    r = post(client, slug, headers)
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid signature"
    assert db.events_for(slug) == []


def test_v2_signed_over_a_different_body(client, db):
    slug = db.add_endpoint()
    r = post(client, slug, v2_headers(body=b'{"hello":"other"}'))
    assert r.status_code == 401


@pytest.mark.parametrize("ts", ["abc", "1700000000.5", "-1", "", " 1700000000", "1_700_000_000", "1e9"])
def test_timestamp_not_an_integer(client, db, ts):
    slug = db.add_endpoint()
    headers = {"X-Webhook-Timestamp": ts, "X-Webhook-Signature-V2": v2(ts)}
    r = post(client, slug, headers)
    assert r.status_code == 401
    assert db.events_for(slug) == []


@pytest.mark.parametrize("drop", ["X-Webhook-Timestamp", "X-Webhook-Signature-V2"])
def test_only_one_v2_header_is_rejected_even_with_valid_v1(client, db, drop):
    slug = db.add_endpoint()
    headers = {**v2_headers(), "X-Webhook-Signature": v1()}
    del headers[drop]
    assert post(client, slug, headers).status_code == 401


def test_non_ascii_signature_is_401_not_500(client, db):
    slug = db.add_endpoint()
    junk = "é".encode("latin-1") * 64  # arrives as a non-ASCII str
    headers = {"X-Webhook-Timestamp": str(int(time.time())), "X-Webhook-Signature-V2": junk}
    assert post(client, slug, headers).status_code == 401
    assert post(client, slug, {"X-Webhook-Signature": junk}).status_code == 401


# ── Duplicate rejection ──────────────────────────────────────────────

def test_same_v2_delivery_twice_is_409(client, db):
    slug = db.add_endpoint()
    headers = v2_headers()
    first = post(client, slug, headers)
    second = post(client, slug, headers)
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "Duplicate delivery"
    assert len(db.events_for(slug)) == 1


def test_duplicate_check_is_per_endpoint(client, db):
    a = db.add_endpoint()
    b = db.add_endpoint()
    headers = v2_headers()
    assert post(client, a, headers).status_code == 200
    assert post(client, b, headers).status_code == 200


def test_duplicate_outside_dedupe_window_is_not_409(client, db):
    slug = db.add_endpoint()
    headers = v2_headers()
    assert post(client, slug, headers).status_code == 200
    db.events_for(slug)[0]["received_at"] -= routes.INBOUND_DUPLICATE_WINDOW_SECONDS + 1
    assert post(client, slug, headers).status_code == 200


def test_new_timestamp_same_body_is_not_a_duplicate(client, db):
    slug = db.add_endpoint()
    now = int(time.time())
    assert post(client, slug, v2_headers(now)).status_code == 200
    assert post(client, slug, v2_headers(now - 1)).status_code == 200
    assert len(db.events_for(slug)) == 2


def test_v1_deliveries_are_not_deduplicated(client, db):
    """V1 has no timestamp, so identical bodies are legitimately repeated."""
    slug = db.add_endpoint()
    h = {"X-Webhook-Signature": v1()}
    assert post(client, slug, h).status_code == 200
    assert post(client, slug, h).status_code == 200
    assert len(db.events_for(slug)) == 2


# ── V1 back-compat and require_signature_v2 ──────────────────────────

def test_v1_only_accepted_when_v2_not_required(client, db):
    slug = db.add_endpoint(require_v2=False)
    r = post(client, slug, {"X-Webhook-Signature": v1()})
    assert r.status_code == 200
    assert len(db.events_for(slug)) == 1


def test_v1_only_rejected_when_v2_required(client, db):
    slug = db.add_endpoint(require_v2=True)
    r = post(client, slug, {"X-Webhook-Signature": v1()})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid signature"
    assert db.events_for(slug) == []


def test_v2_accepted_when_v2_required(client, db):
    slug = db.add_endpoint(require_v2=True)
    assert post(client, slug, v2_headers()).status_code == 200


def test_wrong_v1_is_401(client, db):
    slug = db.add_endpoint()
    assert post(client, slug, {"X-Webhook-Signature": v1(secret="nope")}).status_code == 401


def test_no_signature_headers_with_secret_is_401(client, db):
    slug = db.add_endpoint()
    r = post(client, slug, {})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid signature"


@pytest.mark.parametrize("require_v2", [False, True])
def test_no_secret_accepts_unsigned(client, db, require_v2):
    slug = db.add_endpoint(secret=None, require_v2=require_v2)
    r = post(client, slug, {})
    assert r.status_code == 200
    assert len(db.events_for(slug)) == 1


def test_unknown_and_disabled_endpoints_unchanged(client, db):
    assert post(client, "nope", v2_headers()).status_code == 404
    slug = db.add_endpoint(active=False)
    assert post(client, slug, v2_headers()).status_code == 410


# ── Round-trip with the B346 signer ──────────────────────────────────

def test_round_trip_with_b346_sign_headers(client, db):
    slug = db.add_endpoint()
    body = json.dumps({"alert_type": "webhook_test", "severity": "info"}).encode()
    headers = sign_headers(SECRET, body)  # V1 + timestamp + V2, current time
    assert set(headers) == {"X-Webhook-Signature", "X-Webhook-Timestamp", "X-Webhook-Signature-V2"}
    r = post(client, slug, headers, body=body)
    assert r.status_code == 200
    saved = db.events_for(slug)[0]["headers"]
    assert saved["x-webhook-signature-v2"] == headers["X-Webhook-Signature-V2"]
    assert saved["x-webhook-timestamp"] == headers["X-Webhook-Timestamp"]
    # ... and the identical delivery replayed is rejected.
    assert post(client, slug, headers, body=body).status_code == 409


def test_round_trip_b346_signer_with_v2_required(client, db):
    slug = db.add_endpoint(require_v2=True)
    headers = sign_headers(SECRET, BODY)
    assert post(client, slug, headers).status_code == 200


# ── Error bodies stay generic ────────────────────────────────────────

def test_error_bodies_never_echo_expected_values(client, db):
    slug = db.add_endpoint()
    now = int(time.time())
    stale = now - 301
    secrets_in_play = {SECRET, v1(), v2(now), v2(stale)}
    cases = [
        {"X-Webhook-Timestamp": str(stale), "X-Webhook-Signature-V2": v2(stale)},     # expired
        {"X-Webhook-Timestamp": str(now), "X-Webhook-Signature-V2": "0" * 64},       # bad V2
        {"X-Webhook-Timestamp": "abc", "X-Webhook-Signature-V2": "0" * 64},          # bad ts
        {"X-Webhook-Signature": "0" * 64},                                           # bad V1
        {},                                                                          # none
    ]
    good = v2_headers(now)
    post(client, slug, good)
    responses = [post(client, slug, h) for h in cases] + [post(client, slug, good)]  # last: 409
    assert [r.status_code for r in responses] == [401, 401, 401, 401, 401, 409]
    for r in responses:
        assert r.json()["detail"] in {"Invalid signature", "Signature expired", "Duplicate delivery"}
        for value in secrets_in_play:
            assert value not in r.text


# ── Management models and saved-headers allowlist ────────────────────

def test_saved_headers_allowlist_includes_v2_headers():
    assert "x-webhook-signature-v2" in routes._SAVED_EVENT_HEADERS
    assert "x-webhook-timestamp" in routes._SAVED_EVENT_HEADERS


def test_endpoint_models_carry_require_signature_v2():
    assert routes.CreateEndpoint(name="x").require_signature_v2 is False
    assert routes.CreateEndpoint(name="x", require_signature_v2=True).require_signature_v2 is True
    assert routes.UpdateEndpoint().require_signature_v2 is None
    patch = routes.UpdateEndpoint(require_signature_v2=False).model_dump(exclude_none=True)
    assert patch == {"require_signature_v2": False}


def test_migration_003_adds_and_drops_column():
    mig = REPO / "plugins" / "utilities" / "webhooks" / "storage" / "migrations"
    up = (mig / "003_signature_v2_up.sql").read_text()
    down = (mig / "003_signature_v2_down.sql").read_text()
    assert "ADD COLUMN IF NOT EXISTS require_signature_v2 BOOLEAN NOT NULL DEFAULT false" in up
    assert "CREATE TABLE" not in up.upper()
    assert "DROP COLUMN IF EXISTS require_signature_v2" in down
