#!/bin/bash
# NousViz — Server update script
#
# Pulls the latest release from GitHub, runs migrations, rebuilds the
# frontend, and restarts services. Run this on the server.
#
# Usage:
#   ./scripts/update.sh              # update to latest
#   ./scripts/update.sh v0.8.0       # update to specific version
#   ./scripts/update.sh --dry-run    # show what would change
#
# This script does NOT auto-run. The operator must verify and execute.

set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; exit 1; }

cd "$APP_DIR"

# ── Parse args ─────────────────────────────────────────────────────────
TARGET_VERSION=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        v*) TARGET_VERSION="$1"; shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# ── Current state ──────────────────────────────────────────────────────
CURRENT=$(cat VERSION 2>/dev/null || echo "unknown")
echo ""
echo "  NousViz Update"
echo "  Current version: $CURRENT"
echo ""

# ── Check for uncommitted changes ──────────────────────────────────────
if ! git diff --quiet 2>/dev/null; then
    warn "Uncommitted changes detected"
    git status --short | head -5
    echo ""
    read -p "  Continue anyway? [y/N] " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "  Aborted."
        exit 0
    fi
fi

# ── Fetch latest ───────────────────────────────────────────────────────
echo ""
echo "Fetching latest..."
git fetch origin --tags 2>/dev/null

if [ -z "$TARGET_VERSION" ]; then
    TARGET_VERSION=$(git tag --sort=-version:refname | head -1)
fi

if [ -z "$TARGET_VERSION" ]; then
    fail "No tags found. Is this repo connected to GitHub?"
fi

TARGET_CLEAN="${TARGET_VERSION#v}"
CURRENT_CLEAN="${CURRENT%-dev}"

if [ "$TARGET_CLEAN" = "$CURRENT_CLEAN" ]; then
    ok "Already up to date: $CURRENT"
    exit 0
fi

echo "  Updating: $CURRENT → $TARGET_VERSION"

# ── Show what changed ──────────────────────────────────────────────────
echo ""
echo "Changes:"
git log --oneline "HEAD..${TARGET_VERSION}" 2>/dev/null | head -20
COMMIT_COUNT=$(git log --oneline "HEAD..${TARGET_VERSION}" 2>/dev/null | wc -l | tr -d ' ')
echo "  ($COMMIT_COUNT commits)"

if $DRY_RUN; then
    echo ""
    echo "  [DRY RUN] Would update to $TARGET_VERSION"
    echo "  Run without --dry-run to apply."
    exit 0
fi

# ── Confirm ────────────────────────────────────────────────────────────
echo ""
read -p "  Apply update to $TARGET_VERSION? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "  Aborted."
    exit 0
fi

# ── Backup first ───────────────────────────────────────────────────────
echo ""
echo "Creating backup..."
if [ -f scripts/backup.sh ]; then
    bash scripts/backup.sh 2>/dev/null && ok "Backup created" || warn "Backup failed (continuing)"
else
    warn "No backup script found"
fi

# ── Pull ───────────────────────────────────────────────────────────────
echo ""
echo "Pulling $TARGET_VERSION..."
git checkout main 2>/dev/null
git pull origin main 2>/dev/null
ok "Code updated"

# ── Install dependencies ──────────────────────────────────────────────
echo ""
echo "Installing dependencies..."
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
    pip install -r apps/api/requirements.txt -q 2>/dev/null && ok "Python deps" || warn "Python deps failed"
fi
cd apps/web && npm ci --silent 2>/dev/null && ok "Node deps" || warn "Node deps failed"
cd "$APP_DIR"

# ── Run migrations ─────────────────────────────────────────────────────
echo ""
echo "Running migrations..."
for f in storage/postgres/migrations/*.sql; do
    [ -f "$f" ] || continue
    [[ "$f" == *"_down.sql" ]] && continue
    sudo -u postgres psql -d nousviz -f "$f" -q 2>/dev/null
done
ok "Migrations applied"

# ── Build frontend ─────────────────────────────────────────────────────
echo ""
echo "Building frontend..."
cd apps/web && npm run build 2>/dev/null && ok "Frontend built" || fail "Frontend build failed"
cd "$APP_DIR"

# ── Restart services ───────────────────────────────────────────────────
echo ""
echo "Restarting services..."
pm2 reload api --update-env 2>/dev/null && ok "API restarted" || warn "API restart failed"
pm2 reload alerts --update-env 2>/dev/null || true
pm2 reload health-monitor --update-env 2>/dev/null || true
sudo nginx -t 2>/dev/null && sudo systemctl reload nginx 2>/dev/null && ok "Nginx reloaded" || warn "Nginx reload skipped"

# ── Verify ─────────────────────────────────────────────────────────────
echo ""
echo "Verifying..."
sleep 2
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health)
if [ "$HTTP_STATUS" = "200" ]; then
    NEW_VERSION=$(cat VERSION 2>/dev/null || echo "unknown")
    ok "Update complete: $NEW_VERSION"
    echo ""
    echo "  NousViz is running at $(hostname -I 2>/dev/null | awk '{print $1}' || echo 'your server')"
else
    fail "Health check failed (HTTP $HTTP_STATUS) — check logs with: pm2 logs api"
fi
