#!/bin/bash
# NousViz — post-deploy smoke test
#
# Quick verification that critical endpoints work after a deploy.
# Runs automatically at the end of deploy-local.sh.
#
# Usage:
#   ./scripts/smoke-test.sh                     # test localhost:8000
#   ./scripts/smoke-test.sh http://example.com   # test remote server

set -euo pipefail

TARGET="${1:-http://127.0.0.1:8000}"
PASS=0
FAIL=0

green() { echo -e "  \033[0;32m✓\033[0m $1"; PASS=$((PASS+1)); }
red()   { echo -e "  \033[0;31m✗\033[0m $1"; FAIL=$((FAIL+1)); }

check() {
    local name="$1" url="$2" expected_code="$3"
    local actual
    actual=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [[ "$actual" == "$expected_code" ]]; then
        green "$name ($actual)"
    else
        red "$name (expected $expected_code, got $actual)"
    fi
}

check_post() {
    local name="$1" url="$2" body="$3" expected_code="$4"
    local actual
    actual=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$url" \
        -H "Content-Type: application/json" -d "$body" 2>/dev/null || echo "000")
    if [[ "$actual" == "$expected_code" ]]; then
        green "$name ($actual)"
    else
        red "$name (expected $expected_code, got $actual)"
    fi
}

echo ""
echo "  NousViz smoke test — $TARGET"
echo "  ──────────────────────────────"
echo ""

# Health
check "Health endpoint" "$TARGET/api/health" "200"
check "Health config" "$TARGET/api/health/config" "200"
check "Auth status" "$TARGET/api/auth/status" "200"

# Version
VERSION=$(curl -s "$TARGET/api/health" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null || echo "?")
echo "  ℹ Version: $VERSION"

# Query safety
# B207 (v0.9.6.2): hello_items was scrubbed in v0.9.5.5 (B182). Switched
# to avizo_sync_state — a stable per-plugin sync-state table that's part
# of the avizo-jira plugin (v1.0-relevant, owned by the team).
# If avizo-jira is uninstalled in the future, update this to another
# installed plugin's table (any *_sync_state will work).
check_post "Query plugin table (allowed)" \
    "$TARGET/api/query" \
    '{"sql":"SELECT count(*) FROM avizo_sync_state","db_engine":"postgres"}' \
    "200"

check_post "Query core table (blocked)" \
    "$TARGET/api/query" \
    '{"sql":"SELECT * FROM users","db_engine":"postgres"}' \
    "403"

# B207: write operation blocked at the SQL parser before it touches the DB.
# The target table doesn't need to exist — the 403 is parse-level, not
# execution-level. Use a non-existent placeholder so this check carries
# zero risk of an operator misreading it as "we're trying to drop X".
check_post "Write operation (blocked)" \
    "$TARGET/api/query" \
    '{"sql":"DROP TABLE smoke_test_drop_blocked","db_engine":"postgres"}' \
    "403"

# P206 (v0.9.0): end-to-end starter plugin contract. These endpoints
# only exist if the starter plugin is installed AND its api/routes.py
# loaded successfully (SDK importable, broker reachable, role granted).
# If any fail, the plugin contract is broken — fail the deploy.
STARTER_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET/api/plugins/starter-plugin" 2>/dev/null || echo "000")
if [[ "$STARTER_STATUS" == "200" ]]; then
    echo "  Starter plugin detected — running SDK contract checks..."
    check "Starter plugin SDK version" "$TARGET/api/plugins/starter-plugin/sdk-version" "200"
    check "Starter plugin DB contract" "$TARGET/api/plugins/starter-plugin/db-check" "200"
    check "Starter plugin env-check (no secrets in env)" "$TARGET/api/plugins/starter-plugin/env-check" "200"
elif [[ "$STARTER_STATUS" == "404" ]]; then
    echo "  Starter plugin not installed — skipping SDK contract smoke."
    echo "  (Install via UI or /marketplace to activate these checks.)"
else
    red "Starter plugin detail endpoint returned $STARTER_STATUS (unexpected)"
fi

# Removed routes (404 or 401 — auth middleware may intercept before router)
check "Lineage removed" "$TARGET/api/lineage/starter-plugin" "404"
# Accept 401 as well (auth-enabled servers return 401 for unknown routes)
if [[ $FAIL -gt 0 ]]; then
    actual=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET/api/lineage/starter-plugin" 2>/dev/null)
    if [[ "$actual" == "401" ]]; then
        FAIL=$((FAIL-1)); PASS=$((PASS+1))
        green "Lineage removed (401 — auth intercepted, route gone)"
    fi
fi

# Summary
echo ""
echo "  ──────────────────────────────"
if [[ $FAIL -eq 0 ]]; then
    echo -e "  \033[0;32m✓ All $PASS checks passed\033[0m"
else
    echo -e "  \033[0;31m✗ $FAIL of $((PASS+FAIL)) checks failed\033[0m"
    exit 1
fi
echo ""
