#!/bin/bash
# NousViz — local dev launcher
#
# Starts the API server and frontend dev server together.
# Vite hot-reloads on every file change — no stale frontend.
#
# Usage:
#   ./scripts/dev.sh
#
# Stop: Ctrl+C kills both processes cleanly.

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; exit 1; }

# ── Load env ──────────────────────────────────────────────────────────

if [ -f .env ]; then
    set -a; source .env; set +a
    ok "Loaded .env"
else
    warn "No .env found — using defaults (copy .env.example to .env)"
fi

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"

# ── Check venv ────────────────────────────────────────────────────────

if [ ! -f ".venv/bin/activate" ]; then
    fail "No .venv found. Run ./scripts/setup.sh first."
fi

# ── Check node_modules ────────────────────────────────────────────────

if [ ! -d "apps/web/node_modules" ]; then
    echo "  Installing frontend deps..."
    cd apps/web && npm install --silent && cd "$APP_DIR"
    ok "Frontend deps installed"
fi

# ── Find available ports (B103) ──────────────────────────────────────
# Instead of killing whatever is on the port, find the next free one.
# This lets multiple nousviz instances run simultaneously.

find_free_port() {
    local port=$1
    while lsof -ti:${port} >/dev/null 2>&1; do
        port=$((port + 1))
    done
    echo "$port"
}

REQUESTED_API_PORT="$API_PORT"
REQUESTED_WEB_PORT="$WEB_PORT"
API_PORT=$(find_free_port "$API_PORT")
WEB_PORT=$(find_free_port "$WEB_PORT")

# Export so child processes (uvicorn, vite) pick them up
export API_PORT
export WEB_PORT

echo ""
echo "  Starting NousViz dev servers..."
if [ "$API_PORT" != "$REQUESTED_API_PORT" ]; then
    echo "  API  → http://localhost:${API_PORT}  ($REQUESTED_API_PORT was in use)"
else
    echo "  API  → http://localhost:${API_PORT}"
fi
if [ "$WEB_PORT" != "$REQUESTED_WEB_PORT" ]; then
    echo "  Web  → http://localhost:${WEB_PORT}  ($REQUESTED_WEB_PORT was in use)"
else
    echo "  Web  → http://localhost:${WEB_PORT}"
fi
echo "  Stop → Ctrl+C"
echo ""

# ── Cleanup on exit ───────────────────────────────────────────────────

cleanup() {
    echo ""
    echo "  Stopping dev servers..."
    kill $API_PID $WEB_PID 2>/dev/null || true
    wait $API_PID $WEB_PID 2>/dev/null || true
    echo "  Done."
}
trap cleanup EXIT INT TERM

# ── Start API ─────────────────────────────────────────────────────────

source .venv/bin/activate
python3 -m uvicorn apps.api.src.main:app \
    --reload \
    --port "${API_PORT}" \
    --log-level warning \
    2>&1 | sed 's/^/  [api] /' &
API_PID=$!

# ── Start frontend ────────────────────────────────────────────────────

cd apps/web
WEB_PORT="${WEB_PORT}" npm run dev -- --port "${WEB_PORT}" 2>&1 | sed 's/^/  [web] /' &
WEB_PID=$!
cd "$APP_DIR"

# ── Wait ──────────────────────────────────────────────────────────────

wait $API_PID $WEB_PID
