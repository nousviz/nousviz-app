"""
NousViz API integration tests.

Runs against a live API instance. Requires:
  - API running (locally or on server)
  - AUTH_REQUIRED=true with multi-user auth enabled (a superadmin user exists)
  - NOUSVIZ_TEST_API_KEY or NOUSVIZ_TEST_PASSWORD set
  - starter-plugin plugin installed

Usage:
  pytest tests/test_api.py -v
  pytest tests/test_api.py -v --base-url=http://your-server.example.com
"""

import os
import time
import pytest
import httpx

BASE_URL = os.environ.get("NOUSVIZ_TEST_URL", "http://localhost:8000")
API_KEY = os.environ.get("NOUSVIZ_TEST_API_KEY", "")
PASSWORD = os.environ.get("NOUSVIZ_TEST_PASSWORD", "")


@pytest.fixture(scope="session")
def client():
    return httpx.Client(base_url=BASE_URL, timeout=10)


@pytest.fixture(scope="session")
def auth_headers():
    if API_KEY:
        return {"X-API-Key": API_KEY}
    return {}


# ── Health ────────────────────────────────────────────────────────────


def test_health_returns_200(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("healthy", "degraded")
    assert "version" in data
    assert "stats" in data


def test_health_config_returns_200(client):
    r = client.get("/api/health/config")
    assert r.status_code == 200
    data = r.json()
    assert "encryption_key_set" in data
    assert "auth_required" in data


# ── Auth ──────────────────────────────────────────────────────────────


def test_auth_status_public(client):
    r = client.get("/api/auth/status")
    assert r.status_code == 200


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"password": "definitely_wrong_password_12345"})
    assert r.status_code in (401, 503)  # 503 if password not configured


def test_login_rate_limit(client):
    """6 rapid wrong password attempts — 6th should return 429."""
    statuses = []
    for _ in range(7):
        r = client.post("/api/auth/login", json={"password": "wrong"})
        statuses.append(r.status_code)
    # At least one 429 in the batch
    assert 429 in statuses, f"Expected 429 in {statuses}"
    # Wait for rate limit to reset
    time.sleep(61)


# ── Query safety ──────────────────────────────────────────────────────


def test_query_plugin_table_unauthenticated(client):
    """Plugin-declared tables should be queryable without auth."""
    # `db_engine` is a plugin manifest field (dashboards + insights specs), not a request
    # field. `QueryRequest` only accepts sql / database / max_rows. The old test body also
    # set `"db_engine": "postgres"` which Pydantic silently dropped — removed to reflect
    # the actual API contract.
    r = client.post("/api/query", json={
        "sql": "SELECT count(*) AS v FROM hello_items",
    })
    assert r.status_code == 200
    assert r.json()["rows"][0]["v"] >= 0


def test_query_core_table_unauthenticated_blocked(client):
    """Core tables should be blocked for unauthenticated queries."""
    r = client.post("/api/query", json={
        "sql": "SELECT * FROM users",
        "db_engine": "postgres",
    })
    assert r.status_code == 403


def test_query_fusions_table_unauthenticated_blocked(client):
    """Non-plugin tables should be blocked for unauthenticated queries."""
    r = client.post("/api/query", json={
        "sql": "SELECT * FROM fusions",
        "db_engine": "postgres",
    })
    assert r.status_code == 403


def test_query_write_blocked(client):
    """Write operations should always be blocked."""
    r = client.post("/api/query", json={
        "sql": "DROP TABLE hello_items",
        "db_engine": "postgres",
    })
    assert r.status_code == 403


def test_query_with_auth_allows_core_tables(client, auth_headers):
    """Authenticated queries can access non-blocked core tables."""
    if not auth_headers:
        pytest.skip("No API key configured")
    r = client.post("/api/query", json={
        "sql": "SELECT count(*) AS v FROM fusions",
        "db_engine": "postgres",
    }, headers=auth_headers)
    assert r.status_code == 200


# ── Shares ────────────────────────────────────────────────────────────


def test_share_lifecycle(client, auth_headers):
    """Create → access → revoke → access returns 410."""
    if not auth_headers:
        pytest.skip("No API key configured")

    # Create
    r = client.post("/api/shares", json={
        "page_path": "/plugin/starter-plugin/analytics",
        "title": "Test Share",
        "resource_type": "plugin_dashboard",
        "expires_hours": 1,
    }, headers=auth_headers)
    assert r.status_code == 200
    share_id = r.json()["share_id"]

    # Metadata (public)
    r = client.get(f"/api/shares/{share_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Test Share"

    # Access (public, no password)
    r = client.post(f"/api/shares/{share_id}/access", json={})
    assert r.status_code == 200
    assert r.json()["page_path"] == "/plugin/starter-plugin/analytics"

    # Revoke
    r = client.delete(f"/api/shares/{share_id}", headers=auth_headers)
    assert r.status_code == 200

    # Access after revoke
    r = client.get(f"/api/shares/{share_id}")
    assert r.status_code == 410


def test_share_password_protection(client, auth_headers):
    """Password-protected share rejects wrong password."""
    if not auth_headers:
        pytest.skip("No API key configured")

    r = client.post("/api/shares", json={
        "page_path": "/plugin/starter-plugin/analytics",
        "title": "PW Test",
        "resource_type": "plugin_dashboard",
        "password": "secret123",
        "expires_hours": 1,
    }, headers=auth_headers)
    assert r.status_code == 200
    share_id = r.json()["share_id"]

    # Wrong password
    r = client.post(f"/api/shares/{share_id}/access", json={"password": "wrong"})
    assert r.status_code == 401

    # Correct password
    r = client.post(f"/api/shares/{share_id}/access", json={"password": "secret123"})
    assert r.status_code == 200

    # Cleanup
    client.delete(f"/api/shares/{share_id}", headers=auth_headers)


# ── Plugin settings ───────────────────────────────────────────────────


def test_plugin_settings_save_and_read(client, auth_headers):
    """Save a setting, read it back, verify it matches."""
    if not auth_headers:
        pytest.skip("No API key configured")

    # Save
    r = client.post("/api/plugins/starter-plugin/settings", json={
        "settings": [{"key": "item_limit", "value": 42}],
    }, headers=auth_headers)
    assert r.status_code == 200

    # Read
    r = client.get("/api/plugins/starter-plugin/settings", headers=auth_headers)
    assert r.status_code == 200
    settings = {s["key"]: s["value"] for s in r.json()["settings"]}
    assert settings["item_limit"] == 42

    # Restore original
    client.post("/api/plugins/starter-plugin/settings", json={
        "settings": [{"key": "item_limit", "value": 5}],
    }, headers=auth_headers)


# ── Plugin manifest ───────────────────────────────────────────────────


def test_plugin_manifest_public(client):
    """Plugin manifests are publicly readable (GET-only)."""
    r = client.get("/api/plugins/starter-plugin")
    assert r.status_code == 200
    data = r.json()
    assert data["display_name"] == "Starter Plugin"
    assert "databases" in data


def test_plugin_dashboard_spec_public(client):
    """Dashboard specs are publicly readable."""
    r = client.get("/api/plugins/starter-plugin/dashboards/analytics")
    assert r.status_code == 200
    data = r.json()
    assert data["db_engine"] == "postgres"
    assert len(data["panels"]) > 0


# ── B160: plugin admin + plugin-shipped routes require auth ──────────


def test_b160_plugin_admin_routes_require_auth(client, monkeypatch):
    """Endpoints under /api/plugins/<id>/... that aren't manifest /
    dashboard-spec / widget bundle must require a session token.

    Regression for B160 (v0.9.4.9): the previous prefix-based public
    allowlist matched everything under /api/plugins/, leaking plugin
    data + admin endpoints. Now an exact-pattern allowlist gates these.
    """
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    blocked_paths = [
        "/api/plugins/starter-plugin/settings",
        "/api/plugins/starter-plugin/modules",
        "/api/plugins/starter-plugin/sync/status",
        "/api/plugins/starter-plugin/sync-schedule",
        "/api/plugins/starter-plugin/connections",
        "/api/plugins/starter-plugin/uninstall-check",
        "/api/plugins/audit-log",
        "/api/plugins/updates",
        "/api/plugins/capabilities",
        "/api/plugins/catalog",
    ]
    for path in blocked_paths:
        r = client.get(path)
        assert r.status_code == 401, (
            f"GET {path} without auth must return 401 (got {r.status_code}). B160."
        )


def test_b160_plugin_shipped_route_requires_auth(client, monkeypatch):
    """Plugin-shipped GETs at /api/plugins/<slug>/<arbitrary> must require auth.

    Regression for B160 (v0.9.4.9): plugins like SDI mount routes under
    /api/plugins/<slug>/... — those were unintentionally public. The
    fix narrows the allowlist so only manifest, dashboard-spec, and
    widget-bundle URLs stay public; everything else falls through.
    """
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    # starter-plugin doesn't ship custom data routes, but the middleware
    # decision happens BEFORE routing — so we just need a path that
    # doesn't match the allowlist regex; 401 from middleware is what
    # we're asserting (vs 404 from a missing route).
    r = client.get("/api/plugins/starter-plugin/arbitrary-data-route")
    assert r.status_code == 401, (
        f"plugin-shipped routes must require auth (got {r.status_code}). B160."
    )


# ── Alert sources ─────────────────────────────────────────────────────


def test_alert_sources_no_duplicates(client, auth_headers):
    """Alert data sources should not have duplicates for the same table."""
    if not auth_headers:
        pytest.skip("No API key configured")

    r = client.get("/api/alerts/sources", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()

    # Collect all table names across all source types
    all_tables = []
    for source_list in [data.get("postgres", []), data.get("plugins", [])]:
        for source in source_list:
            all_tables.append(source["table"])

    # Check for duplicates
    seen = set()
    duplicates = []
    for t in all_tables:
        if t in seen:
            duplicates.append(t)
        seen.add(t)

    assert len(duplicates) == 0, f"Duplicate data sources found: {duplicates}"


# ── Query bypass attempts ────────────────────────────────────────────


def test_query_comment_escape_blocked(client):
    """SQL comments shouldn't bypass table restrictions."""
    r = client.post("/api/query", json={
        "sql": "SELECT * FROM /* hello_items */ users"
    })
    assert r.status_code == 403


def test_query_union_bypass_blocked(client):
    """UNION with a blocked table should be rejected."""
    r = client.post("/api/query", json={
        "sql": "SELECT * FROM hello_items UNION SELECT id,email,name,role,'t','','','','' FROM users"
    })
    assert r.status_code == 403


def test_query_subquery_injection_blocked(client):
    """Subquery referencing a blocked table should be rejected."""
    r = client.post("/api/query", json={
        "sql": "SELECT * FROM hello_items WHERE name IN (SELECT email FROM users)"
    })
    assert r.status_code == 403


def test_query_write_in_comment_blocked(client):
    """Write operations hidden in comments should be blocked."""
    r = client.post("/api/query", json={
        "sql": "SELECT 1; -- DROP TABLE hello_items"
    })
    # Should either block the multi-statement or succeed with just SELECT 1
    assert r.status_code in (200, 403)


# ── Auth boundaries ──────────────────────────────────────────────────


def test_auth_expired_token_returns_401(client):
    """An invalid session token should return 401."""
    r = client.get("/api/alerts", headers={"X-Session-Token": "expired_invalid_token_12345"})
    assert r.status_code == 401


def test_auth_malformed_token_returns_401(client):
    """A malformed token should return 401, not 500."""
    r = client.get("/api/alerts", headers={"X-Session-Token": ""})
    assert r.status_code == 401


def test_auth_no_token_returns_401(client):
    """No auth headers at all should return 401 on protected endpoints."""
    r = client.get("/api/alerts")
    assert r.status_code == 401


# ── RBAC enforcement ─────────────────────────────────────────────────


def test_rbac_viewer_cannot_create_alert(client):
    """Viewer role should get 403 on alert creation."""
    # Use an invalid token — this tests the auth layer, not a real viewer
    r = client.post("/api/alerts", json={
        "name": "test", "label": "Test", "plugin_id": "core",
        "dataset": "hello_items", "metric": "id", "condition_type": "zero_check",
    }, headers={"X-Session-Token": "fake_viewer_token"})
    assert r.status_code in (401, 403)


def test_rbac_unauthenticated_cannot_create_fusion(client):
    """Unauthenticated user should get 401 on fusion creation."""
    r = client.post("/api/fusions", json={
        "name": "test-fusion", "label": "Test", "widgets": [],
    })
    assert r.status_code == 401


def test_rbac_unauthenticated_cannot_delete_annotation(client):
    """Unauthenticated user should get 401 on annotation deletion."""
    r = client.delete("/api/annotations/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 401


def test_rbac_unauthenticated_cannot_install_plugin(client):
    """Unauthenticated user should get 401 on plugin install."""
    r = client.post("/api/plugins/fake-plugin/install", json={})
    assert r.status_code == 401


def test_rbac_unauthenticated_cannot_create_share(client):
    """Unauthenticated user should get 401 on share creation."""
    r = client.post("/api/shares", json={
        "resource_type": "dashboard", "page_path": "/test",
    })
    assert r.status_code == 401


def test_rbac_unauthenticated_cannot_create_note(client):
    """Unauthenticated user should get 401 on note creation."""
    r = client.post("/api/notes", json={
        "page_path": "/test", "content": "test note",
    })
    assert r.status_code == 401


# ── Plugin contract smoke ────────────────────────────────────────────


def test_hello_plugin_manifest_valid(client):
    """starter-plugin manifest should have required fields."""
    r = client.get("/api/plugins/starter-plugin")
    if r.status_code == 404:
        pytest.skip("starter-plugin not installed")
    assert r.status_code == 200
    data = r.json()
    assert data.get("name") == "starter-plugin"
    assert "databases" in data
    assert "postgres" in data["databases"]
    assert len(data["databases"]["postgres"]["tables"]) >= 2


def test_hello_plugin_dashboards_exist(client):
    """All declared dashboards should be fetchable."""
    r = client.get("/api/plugins/starter-plugin")
    if r.status_code == 404:
        pytest.skip("starter-plugin not installed")
    data = r.json()
    for dash in data.get("dashboards", []):
        dr = client.get(f"/api/plugins/starter-plugin/dashboards/{dash['name']}")
        assert dr.status_code == 200, f"Dashboard {dash['name']} not found"


# ── Shares auth regression ───────────────────────────────────────────


def test_share_list_requires_auth(client):
    """Listing shares should require auth."""
    r = client.get("/api/shares")
    assert r.status_code == 401


def test_share_update_requires_auth(client):
    """Updating a share should require auth."""
    r = client.patch("/api/shares/00000000-0000-0000-0000-000000000000", json={"title": "x"})
    assert r.status_code == 401


def test_share_revoke_requires_auth(client):
    """Revoking a share should require auth."""
    r = client.delete("/api/shares/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 401


def test_share_access_is_public(client):
    """Share access endpoint should not require auth (password checked by endpoint)."""
    r = client.post("/api/shares/00000000-0000-0000-0000-000000000000/access", json={"password": "test"})
    # Should get 404 (share not found), not 401
    assert r.status_code in (404, 400)


# ── Admin CLI ────────────────────────────────────────────────────────


def test_admin_cli_requires_auth(client):
    """Admin CLI should require authentication."""
    r = client.post("/api/admin/cli", json={"command": "help"})
    assert r.status_code == 401
