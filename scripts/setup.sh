#!/bin/bash
# NousViz — First-time setup script
#
# Supports: macOS (Homebrew), Ubuntu/Debian, RHEL/Fedora/CentOS, Arch Linux
# Windows users: see docs/windows-setup.md or use WSL2
#
# Usage:
#   ./scripts/setup.sh            # local dev setup (default)
#   ./scripts/setup.sh --server   # server/production setup (adds frontend build + pm2)

set -euo pipefail

# ── Parse flags ───────────────────────────────────────────────────────
SERVER_MODE=false
for arg in "$@"; do
    case "$arg" in
        --server) SERVER_MODE=true ;;
    esac
done

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"

# B245 (v0.9.11.1): warn if --server install is under /root or another
# directory nginx can't traverse. nginx runs as www-data and needs
# +x on every parent dir up to apps/web/dist; /root is mode 700.
# /opt and /srv are the conventional locations.
if [[ "$SERVER_MODE" == true ]] && [[ "$APP_DIR" == /root/* || "$APP_DIR" == /home/*/* ]]; then
    echo ""
    echo "  ⚠ Server install detected under $APP_DIR"
    echo "    nginx runs as www-data and may not be able to read this path."
    echo "    Recommended location: /opt/nousviz or /srv/nousviz."
    echo "    To move:"
    echo "      sudo mv $APP_DIR /opt/nousviz"
    echo "      cd /opt/nousviz && sudo ./scripts/setup.sh --server"
    echo ""
    echo "    Continuing in 5 seconds — Ctrl-C to abort."
    sleep 5
fi

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; exit 1; }

# ── Detect OS ─────────────────────────────────────────────────────────
OS=""
DISTRO=""
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ -f /etc/os-release ]]; then
    OS="linux"
    . /etc/os-release
    DISTRO="${ID:-unknown}"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    echo ""
    echo "Windows detected. Please use one of:"
    echo "  • WSL2 (recommended): https://learn.microsoft.com/windows/wsl/"
    echo "  • Then re-run this script inside WSL2"
    exit 1
else
    OS="unknown"
fi

echo "═══════════════════════════════════════"
echo "  NousViz Setup"
echo "  OS: $OS${DISTRO:+ ($DISTRO)}"
echo "═══════════════════════════════════════"
echo ""

# ── 1. Environment file ───────────────────────────────────────────────
if [ ! -f .env ]; then
    echo "[1/7] Creating .env from .env.example..."
    cp .env.example .env
    ok ".env created — edit before production use"
else
    echo "[1/7] .env already exists ✓"
fi

# Parse .env — strip inline comments so values are clean
set -a
while IFS='=' read -r key value; do
    [[ "$key" =~ ^#.*$|^[[:space:]]*$ ]] && continue
    value="${value%%#*}"
    value="${value%"${value##*[![:space:]]}"}"
    [[ -n "$key" ]] && export "$key=$value"
done < .env
set +a

PG_HOST="${POSTGRES_HOST:-localhost}"
PG_PORT="${POSTGRES_PORT:-5432}"
PG_DB="${POSTGRES_DB:-nousviz}"
PG_USER="${POSTGRES_USER:-nousviz}"

# S108: no more 'nousviz_dev' default. If POSTGRES_PASSWORD is unset,
# generate a strong random password and persist it to .env so future
# process starts pick it up. setup.sh only runs once per install.
if [ -z "${POSTGRES_PASSWORD:-}" ]; then
    if command -v python3 &>/dev/null; then
        PG_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
    else
        PG_PASS=$(head -c 18 /dev/urandom | base64 | tr -d '=+/\n')
    fi
    echo "  Generated random POSTGRES_PASSWORD (saving to .env)"
    if grep -q "^POSTGRES_PASSWORD=" .env; then
        # macOS-compatible sed -i
        sed -i.bak "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$PG_PASS|" .env && rm -f .env.bak
    else
        echo "POSTGRES_PASSWORD=$PG_PASS" >> .env
    fi
    export POSTGRES_PASSWORD="$PG_PASS"
else
    PG_PASS="$POSTGRES_PASSWORD"
fi

# ── Enforce NOUSVIZ_ENCRYPTION_KEY ────────────────────────────────────
if [ -z "${NOUSVIZ_ENCRYPTION_KEY:-}" ]; then
    echo "  Generating NOUSVIZ_ENCRYPTION_KEY..."
    if command -v python3 &>/dev/null; then
        NEW_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        # Write it into .env (replace the empty line)
        if grep -q "^NOUSVIZ_ENCRYPTION_KEY=" .env; then
            sed -i.bak "s|^NOUSVIZ_ENCRYPTION_KEY=.*|NOUSVIZ_ENCRYPTION_KEY=$NEW_KEY|" .env && rm -f .env.bak
        else
            echo "NOUSVIZ_ENCRYPTION_KEY=$NEW_KEY" >> .env
        fi
        export NOUSVIZ_ENCRYPTION_KEY="$NEW_KEY"
        ok "NOUSVIZ_ENCRYPTION_KEY generated and saved to .env"
        warn "Record this key — losing it means losing access to stored credentials."
    else
        fail "python3 not found — cannot generate NOUSVIZ_ENCRYPTION_KEY.
  Set it manually in .env:
    NOUSVIZ_ENCRYPTION_KEY=\$(python3 -c \"import secrets; print(secrets.token_hex(32))\")"
    fi
else
    ok "NOUSVIZ_ENCRYPTION_KEY already set"
fi

# ── Enforce NOUSVIZ_PLUGIN_PASSWORD (P203 / v0.9.0) ───────────────────
# The nousviz_plugin Postgres role's password. Plugin subprocesses
# connect as this role (via the credential broker, never env) to get
# a privilege-scoped DB connection. Generated once; stable across
# re-runs of setup.sh.
if [ -z "${NOUSVIZ_PLUGIN_PASSWORD:-}" ]; then
    echo "  Generating NOUSVIZ_PLUGIN_PASSWORD..."
    if command -v python3 &>/dev/null; then
        PLUGIN_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        if grep -q "^NOUSVIZ_PLUGIN_PASSWORD=" .env; then
            sed -i.bak "s|^NOUSVIZ_PLUGIN_PASSWORD=.*|NOUSVIZ_PLUGIN_PASSWORD=$PLUGIN_PASS|" .env && rm -f .env.bak
        else
            echo "NOUSVIZ_PLUGIN_PASSWORD=$PLUGIN_PASS" >> .env
        fi
        export NOUSVIZ_PLUGIN_PASSWORD="$PLUGIN_PASS"
        ok "NOUSVIZ_PLUGIN_PASSWORD generated and saved to .env"
    else
        fail "python3 not found — cannot generate NOUSVIZ_PLUGIN_PASSWORD."
    fi
else
    PLUGIN_PASS="$NOUSVIZ_PLUGIN_PASSWORD"
    ok "NOUSVIZ_PLUGIN_PASSWORD already set"
fi

# ── 2. Ensure Postgres is running ─────────────────────────────────────
echo "[2/7] Checking Postgres..."

pg_running() {
    python3 -c "
import socket, sys
s = socket.socket()
s.settimeout(1)
try:
    s.connect(('$PG_HOST', $PG_PORT))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null
}

wait_for_pg() {
    for i in $(seq 1 20); do
        pg_running && return 0
        sleep 1
    done
    return 1
}

install_postgres_macos() {
    if ! command -v brew &>/dev/null; then
        fail "Homebrew is required to install Postgres on macOS.
  Install it: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    fi
    echo "  Installing postgresql@16 via Homebrew..."
    brew install postgresql@16 -q
    brew services start postgresql@16
    export PATH="/opt/homebrew/opt/postgresql@16/bin:/usr/local/opt/postgresql@16/bin:$PATH"
}

install_postgres_debian() {
    echo "  Installing postgresql via apt..."
    # B244 (v0.9.11.0): DEBIAN_FRONTEND=noninteractive silences the
    # "debconf: unable to initialize frontend: Dialog" cascade on droplets
    # that don't expose a controlling tty.
    sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q postgresql postgresql-contrib
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
}

install_postgres_rhel() {
    echo "  Installing postgresql via dnf/yum..."
    if command -v dnf &>/dev/null; then
        sudo dnf install -y -q postgresql-server postgresql-contrib
    else
        sudo yum install -y -q postgresql-server postgresql-contrib
    fi
    sudo postgresql-setup --initdb 2>/dev/null || sudo postgresql-setup initdb 2>/dev/null || true
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
}

install_postgres_arch() {
    echo "  Installing postgresql via pacman..."
    sudo pacman -S --noconfirm postgresql
    sudo -u postgres initdb -D /var/lib/postgres/data
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
}

start_existing_postgres_macos() {
    # Try to start any already-installed postgresql formula
    local formula
    formula=$(brew list 2>/dev/null | grep -E '^postgresql(@[0-9]+)?$' | sort -V | tail -1 || true)
    if [ -n "$formula" ]; then
        brew services start "$formula" >/dev/null 2>&1 || true
        # Add formula bin to PATH
        local prefix
        prefix=$(brew --prefix "$formula" 2>/dev/null || echo "")
        [ -n "$prefix" ] && export PATH="$prefix/bin:$PATH"
        return 0
    fi
    return 1
}

start_existing_postgres_linux() {
    # Try pg_ctlcluster (Debian) or systemctl
    if command -v pg_ctlcluster &>/dev/null; then
        sudo pg_ctlcluster "$(pg_lsclusters -h | awk '{print $1}' | head -1)" main start 2>/dev/null || true
    elif command -v systemctl &>/dev/null; then
        sudo systemctl start postgresql 2>/dev/null || true
    fi
}

if pg_running; then
    ok "Postgres already running on $PG_HOST:$PG_PORT"
else
    # Try starting an existing install first
    if [[ "$OS" == "macos" ]]; then
        start_existing_postgres_macos 2>/dev/null || true
    else
        start_existing_postgres_linux 2>/dev/null || true
    fi

    if wait_for_pg 2>/dev/null; then
        ok "Postgres started"
    else
        # Need to install
        case "$OS" in
            macos)
                install_postgres_macos
                ;;
            linux)
                case "$DISTRO" in
                    ubuntu|debian|linuxmint|pop|raspbian)
                        install_postgres_debian
                        ;;
                    rhel|centos|fedora|rocky|almalinux|ol)
                        install_postgres_rhel
                        ;;
                    arch|manjaro|endeavouros)
                        install_postgres_arch
                        ;;
                    *)
                        # Try apt then dnf then yum
                        if command -v apt-get &>/dev/null; then
                            install_postgres_debian
                        elif command -v dnf &>/dev/null; then
                            install_postgres_rhel
                        elif command -v pacman &>/dev/null; then
                            install_postgres_arch
                        else
                            fail "Cannot auto-install Postgres on $DISTRO.
  Please install PostgreSQL manually and re-run setup:
    https://www.postgresql.org/download/linux/"
                        fi
                        ;;
                esac
                ;;
            *)
                fail "Unsupported OS. Install PostgreSQL manually and re-run:
  https://www.postgresql.org/download/"
                ;;
        esac

        wait_for_pg || fail "Postgres installed but not reachable on $PG_HOST:$PG_PORT.
  Check your Postgres service and re-run setup."
        ok "Postgres installed and running"
    fi
fi

# Add Postgres bin to PATH for psql
export PATH="/opt/homebrew/opt/postgresql@16/bin:/opt/homebrew/opt/postgresql@17/bin:/usr/local/opt/postgresql@16/bin:$PATH"

# ── 3. Create database and user ───────────────────────────────────────
echo "[3/7] Ensuring database '$PG_DB' and user '$PG_USER' exist..."

# OS-aware superuser bootstrap:
#   macOS (Homebrew): current user is a Postgres superuser — use TCP
#   Linux (Ubuntu/Debian/etc): postgres system user via socket — always works, no password needed
if [[ "$OS" == "macos" ]]; then
    run_as_super() { psql -h "$PG_HOST" -p "$PG_PORT" -U "$USER" -d postgres "$@"; }
else
    run_as_super() { sudo -u postgres psql -d postgres "$@"; }
fi

if run_as_super -c "SELECT 1" >/dev/null 2>&1; then
    run_as_super -c "
        DO \$\$ BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$PG_USER') THEN
                CREATE USER $PG_USER WITH PASSWORD '$PG_PASS';
            END IF;
        END \$\$;
    " >/dev/null 2>&1 || true

    run_as_super -tc "SELECT 1 FROM pg_database WHERE datname='$PG_DB'" \
        | grep -q 1 \
        || run_as_super -c "CREATE DATABASE $PG_DB OWNER $PG_USER;" >/dev/null 2>&1

    run_as_super -c "GRANT ALL PRIVILEGES ON DATABASE $PG_DB TO $PG_USER;" >/dev/null 2>&1 || true

    # Ensure the read-only query role exists and is granted to the app user (B101).
    # This must run as superuser because the app user may not have permission
    # to create roles or grant membership on a shared cluster.
    run_as_super -c "
        DO \$\$ BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'nousviz_query') THEN
                CREATE ROLE nousviz_query NOLOGIN;
            END IF;
        END \$\$;
        GRANT nousviz_query TO $PG_USER WITH ADMIN OPTION;
    " >/dev/null 2>&1 || true

    # P203 (v0.9.0): plugin-scoped login role. Plugin subprocesses
    # connect as this role (never as $PG_USER) for privilege separation.
    # The role is LOGIN (has a password); specific grants happen via
    # migration 047 and the plugin install flow.
    run_as_super -c "
        DO \$\$ BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'nousviz_plugin') THEN
                CREATE ROLE nousviz_plugin LOGIN PASSWORD '$PLUGIN_PASS';
            ELSE
                ALTER ROLE nousviz_plugin WITH LOGIN PASSWORD '$PLUGIN_PASS';
            END IF;
        END \$\$;
    " >/dev/null 2>&1 || warn "nousviz_plugin role create/update failed — plugin subprocesses will not be able to connect."

    ok "Database and user ready"
else
    warn "Could not connect as Postgres superuser. Attempting to proceed assuming DB exists."
    warn "If setup fails, manually run:"
    if [[ "$OS" == "macos" ]]; then
        warn "  psql -U \$USER -d postgres -c \"CREATE USER $PG_USER WITH PASSWORD '$PG_PASS';\""
        warn "  psql -U \$USER -d postgres -c \"CREATE DATABASE $PG_DB OWNER $PG_USER;\""
    else
        warn "  sudo -u postgres psql -c \"CREATE USER $PG_USER WITH PASSWORD '$PG_PASS';\""
        warn "  sudo -u postgres psql -c \"CREATE DATABASE $PG_DB OWNER $PG_USER;\""
    fi
fi

# ── 4. Python virtual environment ─────────────────────────────────────
echo "[4/7] Setting up Python environment..."

# Ensure python3 exists
if ! command -v python3 &>/dev/null; then
    fail "python3 not found. Install Python 3.11+:
  macOS:  brew install python@3.12
  Debian: sudo apt-get install python3 python3-venv python3-pip
  RHEL:   sudo dnf install python3"
fi

# Check Python version — 3.10–3.12 required; 3.13+ not yet supported
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
if [ "$PY_MAJOR" -ne 3 ] || [ "$PY_MINOR" -lt 10 ]; then
    fail "Python 3.10–3.12 is required (found Python $PY_MAJOR.$PY_MINOR).
  Install a supported version:
  macOS:  brew install python@3.12
  Linux:  https://www.python.org/downloads/"
elif [ "$PY_MINOR" -ge 13 ]; then
    warn "Python 3.$PY_MINOR detected. Supported range is 3.10–3.12.
  Some compiled dependencies (e.g. cryptography) may fail to install.
  Install Python 3.12 for a reliable setup:
    macOS:  brew install python@3.12 && brew link python@3.12
    Linux:  https://www.python.org/downloads/release/python-3120/"
else
    ok "Python $PY_MAJOR.$PY_MINOR — supported"
fi

if [ ! -d .venv ]; then
    # Ubuntu/Debian ship python3-venv separately from python3.
    # v0.9.11.22.2: the prior unconditional apt-get without sudo killed
    # the script under `set -euo pipefail` on the GitHub Actions runner
    # (apt-get exits 100 without root). Only attempt the install when
    # the venv module is actually missing AND sudo is available; the
    # fallback is the clearer error from `python3 -m venv` itself.
    if [[ "$OS" == "linux" ]] && command -v apt-get &>/dev/null; then
        if ! python3 -c "import venv" 2>/dev/null && command -v sudo &>/dev/null; then
            sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q python3-venv python3-pip >/dev/null 2>&1 || true
        fi
    fi
    python3 -m venv .venv
    ok ".venv created"
else
    ok ".venv already exists"
fi

.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r apps/api/requirements.txt

# Verify cryptography installed — fails silently under Python 3.13+ otherwise
if ! .venv/bin/python3 -c "import cryptography" 2>/dev/null; then
    warn "The 'cryptography' package failed to install (likely a Python version issue)."
    warn "Try: .venv/bin/pip install cryptography --only-binary=all"
    warn "Or install Python 3.12 and re-run setup."
    warn "Without it, credential storage will not work."
else
    ok "API dependencies installed"
fi

# P201 (v0.9.0): verify nousviz_sdk importable in the venv.
# The `-e ./sdk` line in requirements.txt should have installed it; this
# check catches any silent failure before the API tries to load plugins.
if ! .venv/bin/python3 -c "import nousviz_sdk; print(f'  SDK {nousviz_sdk.__version__}')" 2>/dev/null; then
    fail "nousviz_sdk failed to import. Check that sdk/ exists and pip install succeeded. Plugins will not load routes until this is fixed."
else
    ok "nousviz_sdk importable ($(.venv/bin/python3 -c 'import nousviz_sdk; print(nousviz_sdk.__version__)'))"
fi

# P208 (v0.9.0): create the credential broker's socket directory. The
# broker itself will chmod 0700 on startup, but the directory must exist
# and be writable by the worker user BEFORE the worker boots.
RUN_DIR="$APP_DIR/run"
if [ ! -d "$RUN_DIR" ]; then
    mkdir -p "$RUN_DIR"
    chmod 700 "$RUN_DIR"
    ok "Created credential broker socket dir $RUN_DIR (mode 700)"
else
    chmod 700 "$RUN_DIR" 2>/dev/null || true
    ok "Credential broker socket dir exists ($RUN_DIR)"
fi

# ── 5. Frontend dependencies ──────────────────────────────────────────
echo "[5/7] Installing frontend dependencies..."

# Server mode requires Node.js — install it if missing
if [[ "$SERVER_MODE" == true ]] && ! command -v npm &>/dev/null; then
    echo "  Installing Node.js 20 LTS..."
    if command -v apt-get &>/dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null 2>&1
        DEBIAN_FRONTEND=noninteractive apt-get install -y -q nodejs
    elif command -v dnf &>/dev/null; then
        curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - >/dev/null 2>&1
        dnf install -y -q nodejs
    else
        fail "npm not found and could not be installed automatically.
  Install Node.js 20: https://nodejs.org"
    fi
    ok "Node.js $(node -v) installed"
fi

if command -v npm &>/dev/null; then
    if [ -d apps/web ]; then
        cd apps/web && npm install --silent 2>/dev/null && cd "$APP_DIR"
        ok "apps/web dependencies installed"
    fi
else
    warn "npm not found — skipping frontend install. Install Node.js to run the dashboard:
    https://nodejs.org"
fi

# Verify the app user can connect before running migrations.
# If this fails, the DB user wasn't created or pg_hba.conf is blocking password auth.
if ! .venv/bin/python3 -c "
import psycopg2, sys
try:
    psycopg2.connect(
        host='$PG_HOST', port=$PG_PORT, dbname='$PG_DB',
        user='$PG_USER', password='$PG_PASS', connect_timeout=5
    ).close()
except Exception:
    sys.exit(1)
" 2>/dev/null; then
    fail "Cannot connect to Postgres as '$PG_USER'.
  The DB user may not exist, or pg_hba.conf is blocking password auth.
  Fix on Linux:
    sudo -u postgres psql -c \"CREATE USER $PG_USER WITH PASSWORD '$PG_PASS';\"
    sudo -u postgres psql -c \"CREATE DATABASE $PG_DB OWNER $PG_USER;\"
  Then check /etc/postgresql/*/main/pg_hba.conf has 'md5' or 'scram-sha-256'
  for host connections, then: sudo systemctl restart postgresql"
fi

# ── 6. Postgres migrations ────────────────────────────────────────────
echo "[6/7] Running Postgres migrations..."

MIGRATION_DIR="$APP_DIR/storage/postgres/migrations"
if [ -d "$MIGRATION_DIR" ]; then
    # Ensure schema_migrations table exists before checking it
    .venv/bin/python3 - <<PYEOF
import psycopg2
conn = psycopg2.connect(host='$PG_HOST', port=$PG_PORT, dbname='$PG_DB', user='$PG_USER', password='$PG_PASS', sslmode='prefer')
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
        filename   TEXT PRIMARY KEY,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
""")
conn.commit()
conn.close()
PYEOF

    # B244 (v0.9.11.0): only forward migrations are run by this loop.
    # `[0-9]*.sql` matches files starting with a digit (every NNN_*.sql);
    # the `case` skip is defensive documentation-as-code — any future
    # change to the glob still must not pick up *_down.sql files. The
    # *_down.sql files in this directory are MANUAL ROLLBACK procedures,
    # not forward migrations. See storage/postgres/migrations/README.md.
    for f in "$MIGRATION_DIR"/[0-9]*.sql; do
        fname=$(basename "$f")
        case "$fname" in
            *_down.sql)
                # Manual rollback files; never run as forward migrations.
                continue
                ;;
        esac
        # Skip if already applied
        already=$(.venv/bin/python3 - <<PYEOF
import psycopg2
conn = psycopg2.connect(host='$PG_HOST', port=$PG_PORT, dbname='$PG_DB', user='$PG_USER', password='$PG_PASS', sslmode='prefer')
cur = conn.cursor()
cur.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", ('$fname',))
print('yes' if cur.fetchone() else 'no')
conn.close()
PYEOF
)
        if [ "$already" = "yes" ]; then
            echo "  → $fname (already applied, skipping)"
            continue
        fi
        .venv/bin/python3 - <<PYEOF
import psycopg2
conn = psycopg2.connect(host='$PG_HOST', port=$PG_PORT, dbname='$PG_DB', user='$PG_USER', password='$PG_PASS', sslmode='prefer')
cur = conn.cursor()
cur.execute(open('$f').read())
cur.execute("INSERT INTO schema_migrations (filename) VALUES (%s) ON CONFLICT DO NOTHING", ('$fname',))
conn.commit()
conn.close()
PYEOF
        ok "$fname"
    done
else
    warn "No migrations directory found"
fi

# ── 7. Plugin schema setup ────────────────────────────────────────────
echo "[7/7] Checking installed plugin schemas..."
if [ -d "plugins/installed" ] && ls plugins/installed/*/src/setup_schema.py >/dev/null 2>&1; then
    for schema_file in plugins/installed/*/src/setup_schema.py; do
        slug=$(basename "$(dirname "$(dirname "$schema_file")")")
        .venv/bin/python3 "$schema_file" && ok "$slug schema ready" || warn "$slug schema failed"
    done
else
    ok "No plugins installed yet — visit /marketplace after startup"
fi

# ── 7a. Superuser grants for postgres-owned tables (P203 / v0.9.0) ────
# Tables job_runs, app_logs (and possibly others) are owned by the
# postgres superuser, not by $PG_USER. Migration 047 grants `nousviz`'s
# privileges, but those tables aren't owned by `nousviz` so the GRANT
# silently no-ops. Re-issue here as superuser so plugins can heartbeat
# and emit log events.
if run_as_super -c "SELECT 1" >/dev/null 2>&1; then
    run_as_super -d "$PG_DB" -c "
        DO \$\$ BEGIN
            -- B142 (v0.9.2.2): nousviz must own/grant on every core platform
            -- table it writes to. Without these, install of any multi-module
            -- plugin fails with 'permission denied for table plugin_modules'.
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
    " >/dev/null 2>&1 || warn "superuser grants on core platform tables failed — install/sync may fail"
    ok "Core platform tables granted to nousviz / nousviz_plugin"
else
    warn "No superuser access — skipping core platform grants."
    warn "Run manually:  sudo -u postgres psql -d $PG_DB -c \"GRANT SELECT, INSERT, UPDATE, DELETE ON plugin_modules, plugin_settings, plugin_registry, schema_migrations, job_runs, app_logs TO nousviz; GRANT INSERT, SELECT, UPDATE ON job_runs TO nousviz_plugin; GRANT INSERT, SELECT ON app_logs TO nousviz_plugin;\""
fi

# ── 7b. Backfill nousviz_plugin grants (P203 / v0.9.0) ────────────────
# For every installed plugin, grant the nousviz_plugin role CRUD on that
# plugin's declared tables. Idempotent: if grants already exist, Postgres
# no-ops. If the role doesn't exist (setup.sh earlier step failed), we
# skip with a warning instead of erroring.
if [ -d "plugins/installed" ] && ls plugins/installed/*/plugin.yaml >/dev/null 2>&1; then
    .venv/bin/python3 - <<'PYEOF'
import os, sys, yaml
sys.path.insert(0, os.getcwd())
from apps.api.src.plugin_grants import grant_plugin_tables, _role_exists

if not _role_exists():
    print("  nousviz_plugin role not present — skipping backfill.")
    sys.exit(0)

from pathlib import Path
for plugin_yaml in sorted(Path("plugins/installed").glob("*/plugin.yaml")):
    slug = plugin_yaml.parent.name
    try:
        manifest = yaml.safe_load(plugin_yaml.read_text()) or {}
    except Exception as exc:
        print(f"  {slug}: could not parse plugin.yaml — {exc}")
        continue
    try:
        granted = grant_plugin_tables(slug, manifest)
        if granted:
            print(f"  {slug}: granted on {granted}")
        else:
            print(f"  {slug}: no tables to grant (plugin declares no postgres tables, or tables not yet created)")
    except Exception as exc:
        print(f"  {slug}: grant backfill failed — {exc}")
PYEOF
    ok "Plugin grants backfilled"
fi

# ── 8. Server mode: frontend production build + nginx + pm2 ──────────
if [[ "$SERVER_MODE" == true ]]; then
    echo "[8/9] Building frontend for production..."
    cd apps/web && npm run build && cd "$APP_DIR"
    ok "Frontend built → apps/web/dist/"

    # Install nginx if not present (required to serve the React build)
    if ! command -v nginx &>/dev/null; then
        echo "  Installing nginx..."
        if command -v apt-get &>/dev/null; then
            DEBIAN_FRONTEND=noninteractive apt-get install -y -q nginx
        elif command -v dnf &>/dev/null; then
            dnf install -y -q nginx
        elif command -v yum &>/dev/null; then
            yum install -y -q nginx
        else
            warn "nginx not found and could not be installed automatically. Install it manually: apt-get install nginx"
        fi
    fi
    if command -v nginx &>/dev/null; then
        systemctl enable nginx 2>/dev/null || true
        ok "nginx ready"

        # B245 (v0.9.11.1): finish the nginx install end-to-end so the
        # user's only post-setup step is opening http://<ip>/ in a
        # browser. Pre-v0.9.11.1, setup.sh installed nginx but left the
        # symlink + reload as a manual step in the README — confusing
        # mismatch between the script's "configures pm2 + nginx" claim
        # and what it actually did.
        # Patch the root path in nginx.conf to the actual install dir
        # BEFORE copying it into sites-available (must happen first).
        if [[ "$APP_DIR" != "/opt/nousviz" ]]; then
            sed -i "s|root /opt/nousviz/apps/web/dist|root $APP_DIR/apps/web/dist|g" "$APP_DIR/infra/nginx.conf"
        fi
        cp -f "$APP_DIR/infra/nginx.conf" /etc/nginx/sites-available/nousviz
        ln -sf /etc/nginx/sites-available/nousviz /etc/nginx/sites-enabled/nousviz
        rm -f /etc/nginx/sites-enabled/default
        if nginx -t &>/dev/null; then
            systemctl reload nginx
            ok "nginx configured and reloaded"
        else
            warn "nginx -t failed — config not reloaded. Run 'sudo nginx -t' to see why."
        fi
    fi

    echo "[9/9] Configuring pm2 process manager..."
    mkdir -p "$APP_DIR/logs"
    if ! command -v pm2 &>/dev/null; then
        npm install -g pm2 -q
    fi
    # Start or reload — both are safe to run if pm2 is already running
    pm2 start "$APP_DIR/ecosystem.config.js" 2>/dev/null || pm2 reload "$APP_DIR/ecosystem.config.js"
    pm2 save
    # Generate the startup command for the user to paste (can't run it here — needs sudo)
    pm2 startup 2>/dev/null | grep "sudo" | head -1 > /tmp/pm2-startup-cmd.txt 2>/dev/null || true
    ok "pm2 configured"
fi

# ── Done ──────────────────────────────────────────────────────────────
echo ""
if [[ "$SERVER_MODE" == true ]]; then
    echo "═══════════════════════════════════════"
    echo -e "  ${GREEN}Server setup complete!${NC}"
    echo "═══════════════════════════════════════"
    echo ""
    echo "  Services (pm2):"
    echo "    pm2 status"
    echo ""
    echo "  Make pm2 survive reboots:"
    if [ -f /tmp/pm2-startup-cmd.txt ] && [ -s /tmp/pm2-startup-cmd.txt ]; then
        echo "    $(cat /tmp/pm2-startup-cmd.txt)"
    else
        echo "    Run: pm2 startup   then paste the printed sudo command"
    fi
    echo "    pm2 save"
    echo ""
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "your-server-ip")
    echo "  Visit http://$SERVER_IP"
    echo ""
    echo -e "  ${YELLOW}⚠ Security:${NC} open the URL above and complete the setup wizard"
    echo "     before sharing this address. The wizard will let you set a"
    echo "     password and enable authentication."
    echo ""
else
    echo "═══════════════════════════════════════"
    echo -e "  ${GREEN}Setup complete!${NC}"
    echo "═══════════════════════════════════════"
    echo ""
    echo "  Start the API:"
    echo "    source .venv/bin/activate"
    echo "    python3 -m uvicorn apps.api.src.main:app --reload --port ${API_PORT:-8000}"
    echo ""
    echo "  Start the frontend (separate terminal):"
    echo "    cd apps/web && npm run dev"
    echo ""
    echo "  Visit http://localhost:${WEB_PORT:-5173}"
    echo ""
fi
