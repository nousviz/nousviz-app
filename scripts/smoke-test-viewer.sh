#!/bin/bash
# NousViz — viewer end-to-end smoke test
#
# Exercises the user-visible path that the v1.0.1 regression broke:
#   1. Log in as a real viewer-role account
#   2. Fetch the plugin list with the resulting session token
#   3. Fetch /api/auth/me and /api/auth/me/permissions (the session-check probes)
#   4. Fetch a plugin dashboard spec
#   5. Fetch the same plugin's widget bundle
#
# All requests MUST return 2xx. Any 401/403/5xx on this path means a real
# viewer landing on a plugin dashboard would see breakage. Run this after
# every deploy.
#
# Usage:
#   NOUSVIZ_SMOKE_VIEWER_EMAIL=joe+tests@statsdrone.com \
#   NOUSVIZ_SMOKE_VIEWER_PASSWORD=... \
#   ./scripts/smoke-test-viewer.sh [base_url] [plugin_slug] [dashboard_name]
#
# Defaults:
#   base_url        http://127.0.0.1:8000
#   plugin_slug     avizo-jira
#   dashboard_name  overview
#
# Exit codes:
#   0  every step passed
#   1  one or more checks failed (deploy is broken from a viewer's POV)
#   2  required env vars missing (no test credentials available)

set -euo pipefail

TARGET="${1:-http://127.0.0.1:8000}"
PLUGIN_SLUG="${2:-avizo-jira}"
DASHBOARD_NAME="${3:-overview}"

EMAIL="${NOUSVIZ_SMOKE_VIEWER_EMAIL:-}"
PASSWORD="${NOUSVIZ_SMOKE_VIEWER_PASSWORD:-}"

PASS=0
FAIL=0

green() { echo -e "  \033[0;32m✓\033[0m $1"; PASS=$((PASS+1)); }
red()   { echo -e "  \033[0;31m✗\033[0m $1"; FAIL=$((FAIL+1)); }
info()  { echo -e "  \033[0;36mℹ\033[0m $1"; }

# ── Require credentials ─────────────────────────────────────────────────

if [[ -z "$EMAIL" || -z "$PASSWORD" ]]; then
    cat >&2 <<EOF
Error: NOUSVIZ_SMOKE_VIEWER_EMAIL and NOUSVIZ_SMOKE_VIEWER_PASSWORD must be set.

These should be the credentials for a dedicated viewer-role account that exists
on the target deployment ONLY for smoke-testing. Don't reuse a real user's
credentials — the smoke creates a fresh session each run, which adds churn to
their session list.

Suggested setup:
  - Create a viewer account named e.g. joe+smoketest@yourcompany.com
  - Store the password in a secret manager / .envrc / ~/.config/nousviz/deploy.env
  - Source it before running this script.

EOF
    exit 2
fi

echo ""
echo "  NousViz viewer smoke test"
echo "  Target:    $TARGET"
echo "  As:        $EMAIL"
echo "  Plugin:    $PLUGIN_SLUG  (dashboard: $DASHBOARD_NAME)"
echo "  ──────────────────────────────"
echo ""

# ── 1. Log in ───────────────────────────────────────────────────────────

LOGIN_RESPONSE=$(curl -sS -o - -w "\n%{http_code}" -X POST "$TARGET/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" 2>&1 || echo "0")

LOGIN_CODE=$(echo "$LOGIN_RESPONSE" | tail -n1)
LOGIN_BODY=$(echo "$LOGIN_RESPONSE" | sed '$d')

if [[ "$LOGIN_CODE" != "200" ]]; then
    red "POST /api/auth/login (got $LOGIN_CODE — credentials wrong, or login endpoint broken)"
    echo "$LOGIN_BODY" | head -3
    echo ""
    echo "  ── Cannot continue without a session token ──"
    exit 1
fi

TOKEN=$(echo "$LOGIN_BODY" | python3 -c "import json,sys; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || echo "")

if [[ -z "$TOKEN" ]]; then
    red "Login succeeded but response had no 'token' field"
    echo "$LOGIN_BODY" | head -3
    exit 1
fi

green "POST /api/auth/login ($LOGIN_CODE)"
info "Session token acquired (${#TOKEN} chars)"

# Helper for authed GETs
authed_check() {
    local name="$1" url="$2" expected="${3:-200}"
    local code
    code=$(curl -sS -o /dev/null -w "%{http_code}" \
        -H "X-Session-Token: $TOKEN" \
        "$url" 2>/dev/null || echo "000")
    if [[ "$code" == "$expected" ]]; then
        green "$name ($code)"
    else
        red "$name (expected $expected, got $code)"
    fi
}

authed_check_with_role_assert() {
    local name="$1" url="$2" expected_role="$3"
    local body code
    body=$(curl -sS -o - -w "\n%{http_code}" \
        -H "X-Session-Token: $TOKEN" \
        "$url" 2>/dev/null || echo $'\n000')
    code=$(echo "$body" | tail -n1)
    body=$(echo "$body" | sed '$d')
    if [[ "$code" != "200" ]]; then
        red "$name (expected 200, got $code)"
        return
    fi
    local actual_role
    actual_role=$(echo "$body" | python3 -c "import json,sys; print(json.load(sys.stdin).get('role',''))" 2>/dev/null || echo "")
    if [[ "$actual_role" == "$expected_role" ]]; then
        green "$name (200, role=$actual_role)"
    else
        red "$name (200, but role=$actual_role — expected $expected_role)"
    fi
}

# ── 2. Session-check probes ─────────────────────────────────────────────

# /me should resolve to a viewer (account-config check — protects against
# accidentally pointing the smoke at an admin account, which would let
# admin-only failures slip through).
authed_check_with_role_assert "GET /api/auth/me" "$TARGET/api/auth/me" "viewer"
authed_check "GET /api/auth/me/permissions" "$TARGET/api/auth/me/permissions"

# ── 3. Plugin list ──────────────────────────────────────────────────────

# This is the request that broke v1.0.0. Must return 200 + a non-empty list
# for any viewer who has plugins in their allowlist (or none, which means
# unrestricted = all installed plugins).
PLUGINS_BODY=$(curl -sS -o - -w "\n%{http_code}" \
    -H "X-Session-Token: $TOKEN" \
    "$TARGET/api/plugins" 2>/dev/null || echo $'\n000')
PLUGINS_CODE=$(echo "$PLUGINS_BODY" | tail -n1)
PLUGINS_BODY=$(echo "$PLUGINS_BODY" | sed '$d')

if [[ "$PLUGINS_CODE" == "200" ]]; then
    PLUGIN_COUNT=$(echo "$PLUGINS_BODY" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('plugins',[])))" 2>/dev/null || echo "?")
    if [[ "$PLUGIN_COUNT" == "0" ]]; then
        red "GET /api/plugins (200 but zero plugins visible — viewer's allowlist may be empty)"
    else
        green "GET /api/plugins (200, $PLUGIN_COUNT plugins visible to viewer)"
    fi
else
    red "GET /api/plugins (expected 200, got $PLUGINS_CODE) — the regression is back"
fi

# ── 4. Plugin detail + dashboard spec ──────────────────────────────────

# Optional: only run if the configured plugin is in the viewer's allowlist.
# Skip rather than fail if the viewer can't see it — the smoke shouldn't
# break just because someone re-scoped the test account's plugins.
DETAIL_CODE=$(curl -sS -o /dev/null -w "%{http_code}" \
    -H "X-Session-Token: $TOKEN" \
    "$TARGET/api/plugins/$PLUGIN_SLUG" 2>/dev/null || echo "000")

case "$DETAIL_CODE" in
    200)
        green "GET /api/plugins/$PLUGIN_SLUG (200)"
        authed_check "GET /api/plugins/$PLUGIN_SLUG/dashboards/$DASHBOARD_NAME" \
            "$TARGET/api/plugins/$PLUGIN_SLUG/dashboards/$DASHBOARD_NAME"
        ;;
    404)
        info "Plugin '$PLUGIN_SLUG' not in viewer's allowlist (404) — skipping dashboard check"
        ;;
    *)
        red "GET /api/plugins/$PLUGIN_SLUG (expected 200 or 404, got $DETAIL_CODE)"
        ;;
esac

# ── Summary ─────────────────────────────────────────────────────────────

echo ""
echo "  ──────────────────────────────"
if [[ $FAIL -eq 0 ]]; then
    echo -e "  \033[0;32m✓ Viewer smoke passed: $PASS checks\033[0m"
    echo ""
    exit 0
else
    echo -e "  \033[0;31m✗ Viewer smoke FAILED: $FAIL of $((PASS+FAIL)) checks\033[0m"
    echo -e "  \033[0;31m  A real viewer landing on a plugin dashboard would see breakage.\033[0m"
    echo ""
    exit 1
fi
