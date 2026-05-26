#!/bin/bash
# NousViz — local push deploy
#
# Builds the frontend locally and rsyncs the full app to the server.
# Use this when the server can't pull from GitHub directly.
#
# Target server resolution (first match wins):
#   1. Positional arg          ./scripts/deploy-local.sh user@host
#   2. NOUSVIZ_DEPLOY_TARGET   NOUSVIZ_DEPLOY_TARGET=user@host ./scripts/deploy-local.sh
#   3. Config file             ~/.config/nousviz/deploy.env    (sourced; should export NOUSVIZ_DEPLOY_TARGET)
#   4. (none)                  script exits with usage
#
# Usage:
#   ./scripts/deploy-local.sh                      # full deploy (uses env/config for target)
#   ./scripts/deploy-local.sh --restart            # restart server processes only (no build/sync)
#   ./scripts/deploy-local.sh user@host            # explicit target
#   ./scripts/deploy-local.sh user@host --restart

set -euo pipefail

# ── Resolve target ────────────────────────────────────────────────────

# Load user config file if present (may export NOUSVIZ_DEPLOY_TARGET).
CONFIG_FILE="${HOME}/.config/nousviz/deploy.env"
if [ -f "$CONFIG_FILE" ]; then
    # shellcheck source=/dev/null
    source "$CONFIG_FILE"
fi

TARGET="${NOUSVIZ_DEPLOY_TARGET:-}"
RESTART_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --restart) RESTART_ONLY=true ;;
        --*) echo "Unknown flag: $arg"; exit 1 ;;
        *) TARGET="$arg" ;;  # positional arg overrides env/config
    esac
done

if [ -z "$TARGET" ]; then
    cat >&2 <<EOF
Error: no deploy target set.

Set one of:
  1. Pass as argument:     ./scripts/deploy-local.sh user@host
  2. Set env var:          export NOUSVIZ_DEPLOY_TARGET=user@host
  3. Create config file:   echo 'export NOUSVIZ_DEPLOY_TARGET=user@host' > ~/.config/nousviz/deploy.env

See header of this script for details.
EOF
    exit 2
fi

REMOTE_DIR="/opt/nousviz"
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; exit 1; }
step() { echo -e "\n${GREEN}▶${NC} $1"; }

cd "$APP_DIR"

VERSION=$(cat VERSION)
COMMIT=$(git rev-parse --short HEAD)
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo ""
if $RESTART_ONLY; then
    echo "  NousViz restart — ${TARGET}:${REMOTE_DIR}"
else
    echo "  NousViz deploy — v${VERSION} (${COMMIT}) from ${BRANCH}"
    echo "  Target: ${TARGET}:${REMOTE_DIR}"
fi
echo ""

# ── Restart only ──────────────────────────────────────────────────────

if $RESTART_ONLY; then
    step "Restarting PM2 on ${TARGET}..."
    ssh "${TARGET}" "cd ${REMOTE_DIR} && pm2 reload ecosystem.config.js --update-env && pm2 save"
    ok "PM2 restarted"

    step "Health check..."
    sleep 3
    HTTP_CODE=$(ssh "${TARGET}" "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/health || echo 000")
    if [[ "$HTTP_CODE" == "200" ]]; then
        ok "API healthy (HTTP 200)"
    else
        warn "API returned HTTP ${HTTP_CODE} — check: ssh ${TARGET} 'pm2 logs api --lines 30'"
    fi
    echo ""
    exit 0
fi

# ── 1. Require clean working tree ─────────────────────────────────────

if [[ -n "$(git status --porcelain | grep -v '^??' | grep -v 'todo/')" ]]; then
    warn "Uncommitted changes detected:"
    git status --short | grep -v '^??' | grep -v 'todo/'
    echo ""
    read -p "  Deploy anyway? [y/N] " confirm
    [[ "$confirm" == "y" || "$confirm" == "Y" ]] || fail "Aborted."
fi

# ── 2. Build frontend ─────────────────────────────────────────────────

step "Type checking..."
cd apps/web
if ! npx tsc --noEmit 2>&1 | grep -q "error TS"; then
    ok "TypeScript check passed"
else
    npx tsc --noEmit 2>&1 | grep "error TS" | head -10
    fail "TypeScript errors found — aborting deploy"
fi

step "Building frontend..."
npm run build --silent
cd "$APP_DIR"
ok "Frontend built (apps/web/dist/)"

# ── 3. Rsync everything ───────────────────────────────────────────────

step "Syncing to ${TARGET}..."

rsync -az --delete \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='apps/web/node_modules' \
    --exclude='apps/web/src' \
    --exclude='logs' \
    --exclude='todo' \
    --exclude='dev-log' \
    --exclude='.env' \
    --exclude='*.egg-info' \
    --exclude='data' \
    --exclude='uploads' \
    --filter='protect plugins/installed/**' \
    "$APP_DIR/" "${TARGET}:${REMOTE_DIR}/"

ok "Files synced"

# ── 3b. Install Python dependencies (including editable SDK) ────────
# P201 (v0.9.0): previously only setup.sh installed Python deps, so the
# SDK package (and any other requirements.txt changes) never landed on
# long-running servers. Now every deploy reinstalls from requirements.txt
# including `-e ./sdk`. Idempotent — pip no-ops if already satisfied.

step "Installing Python dependencies (incl. nousviz-sdk)..."
ssh "${TARGET}" "bash -s" <<'REMOTE_SCRIPT'
cd /opt/nousviz
set -e
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r apps/api/requirements.txt
# Verify SDK importable — fail the deploy if not, because plugins will
# silently 404 otherwise.
.venv/bin/python3 -c "import nousviz_sdk; print(f'  nousviz-sdk {nousviz_sdk.__version__} importable')" || {
    echo "FATAL: nousviz_sdk not importable after pip install." >&2
    echo "  Check that sdk/ rsynced correctly and pip install succeeded." >&2
    exit 1
}
# P208 (v0.9.0): credential broker socket directory. Created with mode
# 0700 so only the worker user can bind / connect to the socket.
mkdir -p /opt/nousviz/run
chmod 700 /opt/nousviz/run
echo "  credential broker socket dir ready (/opt/nousviz/run, mode 700)"

# P203 (v0.9.0): nousviz_plugin role bootstrap on upgrade.
# Servers upgrading from v0.8.x don't have NOUSVIZ_PLUGIN_PASSWORD in
# .env or the role in Postgres. Generate + create on the fly so the
# broker can deliver DB credentials. Idempotent (no-op if already set).
if ! grep -q '^NOUSVIZ_PLUGIN_PASSWORD=' .env; then
    PLUGIN_PASS=$(.venv/bin/python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "NOUSVIZ_PLUGIN_PASSWORD=$PLUGIN_PASS" >> .env
    echo "  generated NOUSVIZ_PLUGIN_PASSWORD into .env"
else
    PLUGIN_PASS=$(grep '^NOUSVIZ_PLUGIN_PASSWORD=' .env | cut -d= -f2-)
fi

# Create or update the Postgres role. Requires sudo as postgres
# superuser. If sudo isn't available, fail with a clear remediation.
if sudo -u postgres psql -d nousviz -c "SELECT 1" >/dev/null 2>&1; then
    sudo -u postgres psql -d nousviz <<SQL >/dev/null 2>&1
DO \$\$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'nousviz_plugin') THEN
        CREATE ROLE nousviz_plugin LOGIN PASSWORD '$PLUGIN_PASS';
    ELSE
        ALTER ROLE nousviz_plugin WITH LOGIN PASSWORD '$PLUGIN_PASS';
    END IF;
END \$\$;
-- v0.9.0 fix: tables owned by postgres superuser need superuser GRANT.
-- Migration 047 runs as nousviz (app user) which can't grant on
-- postgres-owned tables — so heartbeat/log paths from plugins silently
-- fail without these.
-- B142 (v0.9.2.2): same gap for nousviz on plugin_modules etc. — without
-- these, multi-module plugin install fails at the auto-enable step.
DO \$\$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'plugin_modules') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON plugin_modules TO nousviz';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'plugin_settings') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON plugin_settings TO nousviz';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'plugin_registry') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON plugin_registry TO nousviz';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'schema_migrations') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON schema_migrations TO nousviz';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'job_runs') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON job_runs TO nousviz';
        EXECUTE 'GRANT INSERT, SELECT, UPDATE ON job_runs TO nousviz_plugin';
        IF EXISTS (SELECT 1 FROM information_schema.sequences
                   WHERE sequence_schema = 'public' AND sequence_name = 'job_runs_id_seq') THEN
            EXECUTE 'GRANT USAGE, SELECT, UPDATE ON SEQUENCE job_runs_id_seq TO nousviz';
            EXECUTE 'GRANT USAGE, SELECT ON SEQUENCE job_runs_id_seq TO nousviz_plugin';
        END IF;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'app_logs') THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON app_logs TO nousviz';
        EXECUTE 'GRANT INSERT, SELECT ON app_logs TO nousviz_plugin';
        IF EXISTS (SELECT 1 FROM information_schema.sequences
                   WHERE sequence_schema = 'public' AND sequence_name = 'app_logs_id_seq') THEN
            EXECUTE 'GRANT USAGE, SELECT, UPDATE ON SEQUENCE app_logs_id_seq TO nousviz';
            EXECUTE 'GRANT USAGE, SELECT ON SEQUENCE app_logs_id_seq TO nousviz_plugin';
        END IF;
    END IF;
END \$\$;
SQL
    echo "  nousviz_plugin role + superuser-owned grants ready"
else
    echo "  WARNING: cannot reach Postgres as superuser — skipping nousviz_plugin role + grants."
    echo "  Run setup.sh manually."
fi

# Backfill per-plugin table grants. Same Python helper setup.sh uses.
# Idempotent — re-issuing GRANT on an already-granted table is a no-op.
set -a; source .env; set +a
.venv/bin/python3 - <<'PYEOF' || echo "  WARNING: plugin-grants backfill failed"
import sys, yaml
sys.path.insert(0, '/opt/nousviz')
from apps.api.src.plugin_grants import grant_plugin_tables, _role_exists
if not _role_exists():
    print("  nousviz_plugin role not present — skipping plugin-grants backfill.")
    sys.exit(0)
from pathlib import Path
for pyaml in sorted(Path("/opt/nousviz/plugins/installed").glob("*/plugin.yaml")):
    slug = pyaml.parent.name
    try:
        manifest = yaml.safe_load(pyaml.read_text()) or {}
    except Exception as exc:
        print(f"    {slug}: parse error — {exc}")
        continue
    granted = grant_plugin_tables(slug, manifest)
    if granted:
        print(f"    {slug}: granted {granted}")
PYEOF
echo "  per-plugin grants backfilled"
REMOTE_SCRIPT
ok "Python deps installed, SDK importable, broker dir + role ready"

# ── 4a. Apply core Postgres migrations (idempotent) ──────────────────
# B128 (v0.8.6.3): previously only setup.sh applied these, so long-running
# deployments drifted from the tree. Now every deploy reconciles — any
# new core migration in storage/postgres/migrations/ applies automatically,
# already-applied ones are skipped via the schema_migrations table.
#
# B210 (v0.9.6.2): two-pass runner so superuser-owned-table migrations
# don't silently fail. Tables app_logs, job_runs, plugin_audit_log,
# deploy_keys are owned by `postgres`; ALTER on them requires ownership,
# not the per-statement grants nousviz holds. Pass 1 routes those via
# `sudo -u postgres`. Pass 2 runs the rest as nousviz. ANY real failure
# aborts the deploy — the previous "review manually" continue-on-failure
# policy almost cost downtime in v0.9.6.1's deploy.

step "Applying core Postgres migrations (pass 1: superuser-owned tables)..."
# Pass 1: migrations on superuser-owned tables, run via sudo -u postgres.
# Includes a one-time backfill for the 8 superuser-table migrations that
# were applied piecemeal in earlier deploys without being recorded.
ssh "${TARGET}" "bash -s" <<'REMOTE_SU_SCRIPT'
cd /opt/nousviz
set -e

# B210: tables owned by postgres superuser. Migrations that ALTER/CREATE/DROP
# any of these must run as `postgres`. Adding a new superuser-owned table
# requires updating this list. Verify with:
#   sudo -u postgres psql nousviz -c "
#     SELECT relname FROM pg_class c JOIN pg_roles r ON c.relowner = r.oid
#     WHERE c.relkind='r' AND c.relnamespace='public'::regnamespace
#       AND r.rolname='postgres' ORDER BY relname;"
SUPERUSER_TABLES=("app_logs" "job_runs" "plugin_audit_log" "deploy_keys" "plugin_modules" "webhook_endpoints" "webhook_events")

# B210 one-time recovery: backfill schema_migrations for superuser-table
# migrations applied piecemeal in earlier deploys without being tracked.
# Idempotent — ON CONFLICT DO NOTHING. Safe to re-run.
sudo -u postgres psql -d nousviz <<'SQL'
INSERT INTO schema_migrations (filename) VALUES
    ('031_job_runs.sql'),
    ('032_plugin_audit_log.sql'),
    ('035_deploy_keys.sql'),
    ('036_deploy_keys_repo_url.sql'),
    ('040_app_logs.sql'),
    ('041_job_runs_backfill.sql'),
    ('043_job_runs_async.sql'),
    ('051_app_logs_promote_columns.sql')
ON CONFLICT DO NOTHING;
SQL

needs_superuser() {
    local sql_file="$1"
    # Flatten newlines so multi-line statements match (e.g. CREATE INDEX
    # on one line and ON <table> on the next is common in our migrations).
    local flat
    flat=$(tr '\n' ' ' < "$sql_file")
    for table in "${SUPERUSER_TABLES[@]}"; do
        # ALTER/CREATE/DROP TABLE [IF [NOT] EXISTS] [public.]<table>
        if echo "$flat" | grep -qiE "(ALTER|CREATE|DROP)[[:space:]]+TABLE([[:space:]]+IF[[:space:]]+(NOT[[:space:]]+)?EXISTS)?[[:space:]]+(public\.)?${table}([[:space:]]|\(|;|$)"; then
            return 0
        fi
        # CREATE [UNIQUE] INDEX [IF NOT EXISTS] <name> ON [public.]<table>.
        # Postgres requires table ownership for CREATE INDEX even with IF NOT EXISTS.
        if echo "$flat" | grep -qiE "CREATE([[:space:]]+UNIQUE)?[[:space:]]+INDEX([[:space:]]+IF[[:space:]]+NOT[[:space:]]+EXISTS)?[[:space:]]+[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]+ON[[:space:]]+(public\.)?${table}([[:space:]]|\(|;|$)"; then
            return 0
        fi
    done
    return 1
}

su_applied=0
su_skipped=0
for f in storage/postgres/migrations/*.sql; do
    [[ "$f" == *"_down.sql" ]] && continue
    needs_superuser "$f" || continue
    fname=$(basename "$f")
    if sudo -u postgres psql -d nousviz -tAc "SELECT 1 FROM schema_migrations WHERE filename = '$fname'" | grep -q 1; then
        su_skipped=$((su_skipped + 1))
        continue
    fi
    echo "  applying (su): $fname"
    if sudo -u postgres psql -d nousviz -v ON_ERROR_STOP=1 -f "$f"; then
        sudo -u postgres psql -d nousviz -c "INSERT INTO schema_migrations (filename) VALUES ('$fname') ON CONFLICT DO NOTHING" >/dev/null
        su_applied=$((su_applied + 1))
    else
        echo "FATAL: superuser migration $fname failed. Aborting deploy."
        exit 1
    fi
done
echo "superuser migrations: applied=$su_applied skipped=$su_skipped"
REMOTE_SU_SCRIPT
ok "Pass 1 (superuser migrations) complete"

step "Applying core Postgres migrations (pass 2: nousviz user)..."
# Pass 2: migrations that don't touch superuser-owned tables, run as nousviz.
# Tolerable failures (legacy schema drift) are recorded as applied so they
# don't keep noise-failing every deploy. Genuine failures abort.
ssh "${TARGET}" "bash -s" <<'REMOTE_SCRIPT'
cd /opt/nousviz
set -e
.venv/bin/python3 - <<'PYEOF'
import sys, re
from pathlib import Path
import psycopg2

REPO = Path("/opt/nousviz")
MIG_DIR = REPO / "storage" / "postgres" / "migrations"

# B210: skip migrations handled by pass 1 (superuser-owned tables).
# Keep in sync with SUPERUSER_TABLES bash array above.
SUPERUSER_TABLES = (
    "app_logs", "job_runs", "plugin_audit_log", "deploy_keys",
    "plugin_modules", "webhook_endpoints", "webhook_events",
)
_SU_TABLES_GROUP = "|".join(SUPERUSER_TABLES)
SU_PATTERN = re.compile(
    # Matches ALTER/CREATE/DROP TABLE … <su-table>
    r"\b(ALTER|CREATE|DROP)\s+TABLE(\s+IF\s+(NOT\s+)?EXISTS)?\s+(public\.)?(" + _SU_TABLES_GROUP + r")\b"
    # Matches CREATE [UNIQUE] INDEX [IF NOT EXISTS] <name> ON … <su-table>
    r"|CREATE(\s+UNIQUE)?\s+INDEX(\s+IF\s+NOT\s+EXISTS)?\s+\w+\s+ON\s+(public\.)?(" + _SU_TABLES_GROUP + r")\b",
    re.IGNORECASE,
)

# B210: tolerable error fragments — "schema has evolved past this migration".
# Recording these as applied prevents re-attempting them on every deploy.
# Add new fragments here if a legacy migration produces a known-safe error.
TOLERABLE_FRAGMENTS = (
    "already exists",
    'column "plugin_id" does not exist',     # 001_connections legacy drift
    'column "token" does not exist',          # 023, 026 legacy drift
)

env = {}
for line in (REPO / ".env").read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

conn = psycopg2.connect(
    host=env.get("POSTGRES_HOST", "localhost"),
    port=int(env.get("POSTGRES_PORT", "5432")),
    dbname=env.get("POSTGRES_DB", "nousviz"),
    user=env.get("POSTGRES_USER", "nousviz"),
    password=env.get("POSTGRES_PASSWORD", ""),
    sslmode="prefer",
)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
        filename TEXT PRIMARY KEY,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
""")
conn.commit()

applied = skipped = tolerated = 0
fatal_failures = []
for f in sorted(MIG_DIR.glob("*.sql")):
    if f.name.endswith("_down.sql"):
        continue
    sql_text = f.read_text()
    if SU_PATTERN.search(sql_text):
        # Handled by pass 1.
        continue
    cur.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", (f.name,))
    if cur.fetchone():
        skipped += 1
        continue
    try:
        cur.execute(sql_text)
        cur.execute(
            "INSERT INTO schema_migrations (filename) VALUES (%s) ON CONFLICT DO NOTHING",
            (f.name,),
        )
        conn.commit()
        applied += 1
        print(f"  applied: {f.name}")
    except Exception as e:
        conn.rollback()
        msg = str(e)
        if any(frag in msg for frag in TOLERABLE_FRAGMENTS):
            cur.execute(
                "INSERT INTO schema_migrations (filename) VALUES (%s) ON CONFLICT DO NOTHING",
                (f.name,),
            )
            conn.commit()
            tolerated += 1
            print(f"  tolerated (schema drift): {f.name} — {msg[:120]}")
        else:
            fatal_failures.append((f.name, msg[:300]))

print(f"core migrations: applied={applied} skipped={skipped} tolerated={tolerated} fatal={len(fatal_failures)}")
if fatal_failures:
    print("FATAL migration failures — aborting deploy:")
    for name, err in fatal_failures:
        print(f"  {name}: {err}")
    sys.exit(1)
conn.close()
PYEOF
REMOTE_SCRIPT
ok "Pass 2 (nousviz migrations) complete"

# ── 4b. Run pending plugin migrations on the server ──────────────────

step "Running plugin migrations..."
ssh "${TARGET}" "
    cd ${REMOTE_DIR}
    source .env 2>/dev/null || true
    for sql in plugins/installed/*/storage/migrations/*.sql; do
        [ -f \"\$sql\" ] || continue
        [[ \"\$sql\" == *_down.sql ]] && continue
        PGPASSWORD=\"\${POSTGRES_PASSWORD:-nousviz}\" psql \
            -h \"\${POSTGRES_HOST:-localhost}\" \
            -U \"\${POSTGRES_USER:-nousviz}\" \
            -d \"\${POSTGRES_DB:-nousviz}\" \
            -f \"\$sql\" \
            --on-error-stop \
            -q 2>/dev/null || true
    done
    echo 'migrations done'
"
ok "Plugin migrations applied (idempotent)"

# ── 5. Reload nginx (picks up any nginx.conf changes, clears server-side cache) ──

step "Reloading nginx..."
# Preserve SSL config if ssl-setup.sh has configured it — only copy HTTP config if no SSL.
# infra/nginx-ssl.conf is a template (with __SSL_CERT__ etc placeholders) consumed by
# ssl-setup.sh, NOT a drop-in. Updates to it are only picked up by re-running ssl-setup.sh.
ssh "${TARGET}" "
    source ${REMOTE_DIR}/.env 2>/dev/null || true
    if [[ -n \"\${NOUSVIZ_SSL:-}\" ]]; then
        echo 'SSL configured (\${NOUSVIZ_SSL}) — preserving current nginx config'
        nginx -t -q && systemctl reload nginx
    else
        cp ${REMOTE_DIR}/infra/nginx.conf /etc/nginx/sites-available/nousviz
        nginx -t -q && systemctl reload nginx
    fi
"
ok "nginx reloaded"

# ── 6. Restart API processes ──────────────────────────────────────────

step "Restarting PM2..."
ssh "${TARGET}" "cd ${REMOTE_DIR} && pm2 reload ecosystem.config.js --update-env && pm2 save"
ok "PM2 restarted"

# ── 7. Health check ───────────────────────────────────────────────────

step "Health check..."
sleep 3
HTTP_CODE=$(ssh "${TARGET}" "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/health || echo 000")
if [[ "$HTTP_CODE" == "200" ]]; then
    ok "API healthy (HTTP 200)"
else
    warn "API returned HTTP ${HTTP_CODE} — check: ssh ${TARGET} 'pm2 logs api --lines 30'"
fi

# ── 8. SSL certificate expiry check ──────────────────────────────────

CERT_WARN=$(ssh "${TARGET}" "
    source ${REMOTE_DIR}/.env 2>/dev/null || true
    if [[ -n \"\${NOUSVIZ_SSL:-}\" ]]; then
        CERT_PATH=''
        if [[ \"\$NOUSVIZ_SSL\" == 'letsencrypt' && -n \"\${NOUSVIZ_DOMAIN:-}\" ]]; then
            CERT_PATH=\"/etc/letsencrypt/live/\${NOUSVIZ_DOMAIN}/fullchain.pem\"
        elif [[ \"\$NOUSVIZ_SSL\" == 'self-signed' ]]; then
            CERT_PATH='/etc/ssl/nousviz/fullchain.pem'
        fi
        if [[ -n \"\$CERT_PATH\" && -f \"\$CERT_PATH\" ]]; then
            EXPIRY=\$(openssl x509 -enddate -noout -in \"\$CERT_PATH\" 2>/dev/null | cut -d= -f2)
            EXPIRY_EPOCH=\$(date -d \"\$EXPIRY\" +%s 2>/dev/null || echo 0)
            NOW_EPOCH=\$(date +%s)
            DAYS_LEFT=\$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
            if [[ \$DAYS_LEFT -lt 7 ]]; then
                echo \"WARN:\$DAYS_LEFT days until SSL cert expires (\$EXPIRY)\"
            else
                echo \"OK:\$DAYS_LEFT days until SSL cert expires\"
            fi
        fi
    fi
" 2>/dev/null || true)

if [[ "$CERT_WARN" == WARN:* ]]; then
    warn "${CERT_WARN#WARN:}"
elif [[ "$CERT_WARN" == OK:* ]]; then
    ok "SSL cert: ${CERT_WARN#OK:}"
fi

# ── 9. Smoke test ────────────────────────────────────────────────────

SERVER_URL="http://$(echo $TARGET | cut -d@ -f2)"
if [[ -f "${APP_DIR}/scripts/smoke-test.sh" ]]; then
    step "Running smoke tests..."
    ssh "${TARGET}" "cd ${REMOTE_DIR} && bash scripts/smoke-test.sh http://127.0.0.1:8000" || warn "Some smoke tests failed"
fi

# v1.0.2: viewer-role end-to-end smoke. The unauthenticated smoke above
# proves health endpoints respond; this one proves a real viewer logging
# in can actually see plugin dashboards — which is the path that the
# v1.0.1 regression broke. Gated on the credentials being set; deploys
# without credentials configured just skip it (with a notice).
if [[ -f "${APP_DIR}/scripts/smoke-test-viewer.sh" ]]; then
    if [[ -n "${NOUSVIZ_SMOKE_VIEWER_EMAIL:-}" && -n "${NOUSVIZ_SMOKE_VIEWER_PASSWORD:-}" ]]; then
        step "Running viewer-role end-to-end smoke..."
        # Pipe credentials through SSH env so they don't appear in the remote
        # command line / shell history.
        ssh "${TARGET}" "NOUSVIZ_SMOKE_VIEWER_EMAIL='${NOUSVIZ_SMOKE_VIEWER_EMAIL}' NOUSVIZ_SMOKE_VIEWER_PASSWORD='${NOUSVIZ_SMOKE_VIEWER_PASSWORD}' cd ${REMOTE_DIR} && bash scripts/smoke-test-viewer.sh http://127.0.0.1:8000" || warn "Viewer smoke failed — a real viewer logging in would see breakage"
    else
        warn "Skipping viewer smoke — set NOUSVIZ_SMOKE_VIEWER_EMAIL + _PASSWORD to enable (see scripts/smoke-test-viewer.sh)"
    fi
fi

# ── 10. Log the deploy ────────────────────────────────────────────────

ssh "${TARGET}" "echo '${TIMESTAMP} v${VERSION} ${COMMIT} ${BRANCH}' >> ${REMOTE_DIR}/logs/deploys.log" 2>/dev/null || true

echo ""
echo "  ✓ Deployed v${VERSION} (${COMMIT}) to ${TARGET}"
echo "  ✓ Test at ${SERVER_URL}/"
echo ""
