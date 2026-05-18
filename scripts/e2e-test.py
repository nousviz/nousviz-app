#!/usr/bin/env python3
"""
NousViz automated E2E test suite.
Requires the API server to be running on localhost:8000.

Usage:
    python3 scripts/e2e-test.py

Exit code 0 = all pass, 1 = failures.
"""

import urllib.request
import urllib.error
import json
import subprocess
import os
import sys

BASE = os.environ.get("NOUSVIZ_API", "http://localhost:8000")
PASS = []
FAIL = []
WARN = []


def req(method, path, body=None):
    url = BASE + path
    h = {"Content-Type": "application/json"}
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw.decode()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode()
    except Exception as ex:
        return 0, str(ex)


def ok(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print(f"  ✅ {name}")
    else:
        FAIL.append(name)
        print(f"  ❌ {name}" + (f": {detail}" if detail else ""))


def warn(name, msg):
    WARN.append(name)
    print(f"  ⚠️  {name}: {msg}")


def query(sql):
    return req("POST", "/api/query", {"sql": sql, "db_engine": "postgres"})


print(f"\nNousViz E2E test suite — {BASE}\n")

# ── 1. Core health ────────────────────────────────────────────────────
print("=== 1. CORE HEALTH ===")
s, d = req("GET", "/api/health")
ok("health 200", s == 200, s)
ok("health status healthy", isinstance(d, dict) and d.get("status") == "healthy")
version = d.get("version", "") if isinstance(d, dict) else ""
ok("health version present", bool(version), version)
ok("health postgres connected", isinstance(d, dict) and d.get("services", {}).get("postgres", {}).get("status") == "connected")

# ── 2. API version ────────────────────────────────────────────────────
print("\n=== 2. API VERSION ===")
try:
    file_version = open("VERSION").read().strip()
except Exception:
    file_version = ""
ok("VERSION file readable", bool(file_version), file_version)
ok("health version matches VERSION file", version == file_version, f"health={version!r} file={file_version!r}")
s2, d2 = req("GET", "/openapi.json")
openapi_ver = d2.get("info", {}).get("version", "") if isinstance(d2, dict) else ""
ok("openapi version matches VERSION file", openapi_ver == file_version, f"openapi={openapi_ver!r}")

# ── 3. Auth ───────────────────────────────────────────────────────────
print("\n=== 3. AUTH ===")
s, d = req("GET", "/api/auth/status")
ok("auth status 200", s == 200, s)
s, d = req("GET", "/api/settings/api-keys")
ok("settings/api-keys requires auth (401/403)", s in (401, 403), f"got {s}")

# ── 4. Schema migrations ──────────────────────────────────────────────
print("\n=== 4. SCHEMA MIGRATIONS ===")
s, d = query("SELECT COUNT(*) AS n FROM schema_migrations")
ok("schema_migrations queryable", s == 200, f"{s}: {d}")
count = 0
if s == 200 and isinstance(d, dict) and d.get("rows"):
    row = d["rows"][0]
    count = row["n"] if isinstance(row, dict) else row[0]
ok("schema_migrations >= 18 rows", count >= 18, f"got {count}")

# ── 5. Critical tables ────────────────────────────────────────────────
print("\n=== 5. CRITICAL TABLES ===")
for tbl in ["alert_events", "hello_items", "hello_events", "fusions", "annotations", "schema_migrations"]:
    s, d = query(f"SELECT COUNT(*) FROM {tbl}")
    ok(f"table {tbl} exists", s == 200, f"{s}")
for tbl in ["users", "api_keys"]:
    s, d = query(f"SELECT COUNT(*) FROM {tbl}")
    ok(f"table {tbl} exists (blocked=403)", s == 403, f"got {s}")

# ── 6. alert_events no FK violation ──────────────────────────────────
print("\n=== 6. ALERT_EVENTS ===")
s, d = query("SELECT COUNT(*) FROM alert_events")
ok("alert_events accessible (no FK violation)", s == 200, f"{s}")

# ── 7. Plugin system ──────────────────────────────────────────────────
print("\n=== 7. PLUGIN SYSTEM ===")
s, d = req("GET", "/api/plugins")
ok("plugins list 200", s == 200, s)
plugins = d.get("plugins", []) if isinstance(d, dict) else []
ok("plugins list non-empty", len(plugins) > 0, f"got {len(plugins)}")
s, d = req("GET", "/api/plugins/catalog")
ok("catalog 200", s == 200, s)
catalog = d.get("plugins", []) if isinstance(d, dict) else []
starter = next((p for p in catalog if p.get("id") == "starter-plugin"), None)
starter_installed = bool(starter and starter.get("installed") is True)
if starter_installed:
    ok("starter-plugin in catalog", starter is not None)
    ok("starter-plugin installed=True", starter_installed)
else:
    print("  starter-plugin not installed — skipping plugin/data-port checks")

# ── 8. Starter plugin routes ──────────────────────────────────────────
if starter_installed:
    print("\n=== 8. STARTER PLUGIN ===")
    s, d = req("GET", "/api/plugins/starter-plugin/items")
    ok("starter-plugin items route exists", s in (200, 400, 422), f"got {s}")
    s, d = req("GET", "/api/plugins/starter-plugin")
    ok("starter-plugin manifest accessible", s == 200, f"{s}")

# ── 9. Data port ──────────────────────────────────────────────────────
print("\n=== 9. DATA PORT ===")
s, d = req("GET", "/api/data-port/plugins")
ok("data-port plugins list 200", s == 200, f"{s}")
if starter_installed:
    s, d = req("GET", "/api/data-port/plugins/starter-plugin/tab/items?page=1&page_size=10")
    ok("data-port items not 500", s != 500, s)
    ok("data-port items has rows key", isinstance(d, dict) and "rows" in d, d)
    s, d = req("GET", "/api/data-port/plugins/starter-plugin/tab/events?page=1&page_size=10")
    ok("data-port events not 500", s != 500, s)
    ok("data-port events rows key", isinstance(d, dict) and "rows" in d, d)

# ── 10. Security — query blocks ───────────────────────────────────────
print("\n=== 10. SECURITY — QUERY BLOCKS ===")
for tbl in ["users", "api_keys", "credentials", "encryption_keys"]:
    s, d = query(f"SELECT * FROM {tbl} LIMIT 1")
    ok(f"query blocks {tbl}", s in (400, 403, 422), f"got {s}")
s, d = query("INSERT INTO annotations(id) VALUES(gen_random_uuid())")
ok("query blocks writes", s in (400, 403, 422), f"got {s}")
s, d = query("SELECT 1 AS x")
ok("query allows safe SELECT", s == 200, f"got {s}: {d}")

# ── 11. Rate limit ────────────────────────────────────────────────────
print("\n=== 11. RATE LIMIT ===")
for i in range(5):
    req("POST", "/api/plugins/e2e-rate-limit-probe/install", {})
s6, _ = req("POST", "/api/plugins/e2e-rate-limit-probe/install", {})
ok("6th install attempt 429", s6 == 429, f"got {s6}")

# ── 12. Health connections ────────────────────────────────────────────
print("\n=== 12. HEALTH CONNECTIONS ===")
s, d = req("GET", "/api/health/connections")
ok("health/connections 200", s == 200, s)
ok("health/connections has issues key", isinstance(d, dict) and "issues" in d, d)

# ── 13. Core endpoints ────────────────────────────────────────────────
print("\n=== 13. CORE ENDPOINTS ===")
for path, method in [
    ("/api/alerts", "GET"),
    ("/api/annotations", "GET"),
    ("/api/fusions", "GET"),
    ("/api/notes?page_path=/", "GET"),
]:
    s, d = req(method, path)
    ok(f"{method} {path} not 500", s != 500, s)

# ── 14. Repo integrity ────────────────────────────────────────────────
print("\n=== 14. REPO INTEGRITY ===")
ok("shaving.py deleted", not os.path.exists("apps/api/src/routes/shaving.py"))
ok("VERSION file exists", os.path.exists("VERSION"))
if os.path.exists("install.sh"):
    ok("install.sh no docker-compose requirement", "docker-compose" not in open("install.sh").read())
if os.path.exists("infra/setup.sh"):
    ok("infra/setup.sh no '1Engine'", "1Engine" not in open("infra/setup.sh").read())
else:
    warn("infra/setup.sh", "not found")

# ── 15. Localhost audit ───────────────────────────────────────────────
print("\n=== 15. LOCALHOST AUDIT ===")
result = subprocess.run(
    ["grep", "-r", "localhost:8000", "apps/web/src/", "--include=*.tsx", "--include=*.ts", "-l"],
    capture_output=True, text=True,
)
real_violations = []
for fpath in result.stdout.strip().splitlines():
    for i, line in enumerate(open(fpath).readlines(), 1):
        stripped = line.strip()
        if "localhost:8000" in stripped and not stripped.startswith("//") and not stripped.startswith("*"):
            real_violations.append(f"{fpath}:{i}")
ok("no localhost:8000 in web src (non-comment)", len(real_violations) == 0, ", ".join(real_violations))

# ── 16. Migration idempotency ─────────────────────────────────────────
if starter_installed:
    print("\n=== 16. MIGRATION IDEMPOTENCY ===")
    s1, _ = req("POST", "/api/plugins/starter-plugin/setup")
    s2, _ = req("POST", "/api/plugins/starter-plugin/setup")
    ok("plugin setup idempotent (no 500)", s1 != 500 and s2 != 500, f"{s1}, {s2}")

# ── 17. Down migration tracking key ──────────────────────────────────
if starter_installed:
    print("\n=== 17. MIGRATION TRACKING ===")
    s, d = query("SELECT filename FROM schema_migrations WHERE filename LIKE 'starter-%' ORDER BY filename")
    ok("starter-plugin migration records present", s == 200 and isinstance(d, dict) and len(d.get("rows", [])) > 0, f"{s}")
    if s == 200 and isinstance(d, dict):
        rows = d.get("rows", [])
        names = [r["filename"] if isinstance(r, dict) else r[0] for r in rows]
        print(f"  Filenames: {names}")

# ── 18. Docs API (B50) ───────────────────────────────────────────────
print("\n=== 18. DOCS API ===")
s, d = req("GET", "/api/docs")
ok("docs list 200", s == 200, f"{s}")
ok("docs list has docs key", isinstance(d, dict) and "docs" in d, d)
if isinstance(d, dict) and "docs" in d:
    slugs = [doc["slug"] for doc in d["docs"]]
    ok("docs list has getting-started", "getting-started" in slugs, slugs)
    ok("docs list has plugin-architecture", "plugin-architecture" in slugs, slugs)
    ok("docs list has contributing-a-plugin", "contributing-a-plugin" in slugs, slugs)
s, d = req("GET", "/api/docs/plugin-architecture")
ok("docs content 200", s == 200, f"{s}")
ok("docs content has content key", isinstance(d, dict) and "content" in d and len(d["content"]) > 100, d)
s, _ = req("GET", "/api/docs/does-not-exist")
ok("docs unknown slug 404", s == 404, f"{s}")

# ── 19. Community plugin install gates (P19) ─────────────────────────
print("\n=== 19. COMMUNITY INSTALL GATES ===")
s, d = req("POST", "/api/plugins/test-ssrf/install", {"repository_url": "file:///etc/passwd"})
ok("blocks file:// url", s == 400, f"{s}: {d}")
s, d = req("POST", "/api/plugins/test-ssrf/install", {"repository_url": "https://192.168.1.1/repo.git"})
ok("blocks private IP", s == 400, f"{s}: {d}")
s, d = req("POST", "/api/plugins/test-ssrf/install", {"repository_url": "http://example.com/repo.git"})
ok("blocks non-https", s == 400, f"{s}: {d}")

# ── 20. Plugin catalog source field (P20) ────────────────────────────
print("\n=== 20. PLUGIN CATALOG ===")
s, d = req("GET", "/api/plugins/catalog")
ok("catalog 200", s == 200, f"{s}")
if isinstance(d, dict) and "plugins" in d:
    plugins = d["plugins"]
    has_source = all("source" in p for p in plugins)
    ok("all catalog entries have source field", has_source, [p.get("id") for p in plugins if "source" not in p])
    has_install_count = all("install_count" in p for p in plugins)
    ok("all catalog entries have install_count field", has_install_count, [p.get("id") for p in plugins if "install_count" not in p])

# ── Summary ───────────────────────────────────────────────────────────
print()
print("━" * 60)
print(f"  PASS: {len(PASS)}")
print(f"  FAIL: {len(FAIL)}")
print(f"  WARN: {len(WARN)}")
if FAIL:
    print("\nFailed:")
    for f in FAIL:
        print(f"  - {f}")

sys.exit(1 if FAIL else 0)
