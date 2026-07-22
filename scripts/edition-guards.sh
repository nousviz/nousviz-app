#!/usr/bin/env bash
# Edition boundary guards (MC-205).
#
# Usage:
#   scripts/edition-guards.sh            # import guard only (any checkout)
#   scripts/edition-guards.sh --public   # + leak guard: enterprise/ must be
#                                        #   physically empty (public builds)
#
# The one-way rule: enterprise imports core; core NEVER imports enterprise.
# Sole sanctioned importer of the add-on: apps/api/src/enterprise_loader.py.
set -uo pipefail

MODE="${1:---all}"
FAIL=0

# ── Import guard (python) ────────────────────────────────────────────
PY_HITS=$(grep -rnE '^[[:space:]]*(from|import)[[:space:]]+(nousviz_enterprise|enterprise)([.[:space:]]|$)' \
  apps packages sdk scripts tests \
  --include='*.py' 2>/dev/null | grep -v 'apps/api/src/enterprise_loader.py' || true)
if [ -n "$PY_HITS" ]; then
  echo "FAIL import-guard (python): core must never import the enterprise add-on:"
  echo "$PY_HITS"
  FAIL=1
else
  echo "PASS import-guard (python)"
fi

# ── Import guard (ts/js) ─────────────────────────────────────────────
TS_HITS=$(grep -rnE "(from[[:space:]]+['\"]|require\(['\"])([^'\"]*/)?(nousviz-)?enterprise" \
  apps/web/src packages/client-ts/src \
  --include='*.ts' --include='*.tsx' --include='*.js' 2>/dev/null || true)
if [ -n "$TS_HITS" ]; then
  echo "FAIL import-guard (ts/js):"
  echo "$TS_HITS"
  FAIL=1
else
  echo "PASS import-guard (ts/js)"
fi

# ── Leak guard (public builds only) ──────────────────────────────────
if [ "$MODE" = "--public" ]; then
  LEAK=$(find enterprise -type f \
    \( -name '*.py' -o -name '*.ts' -o -name '*.js' -o -name '*.tsx' \) 2>/dev/null | head -20 || true)
  if [ -n "$LEAK" ]; then
    echo "FAIL leak-guard: enterprise source present in a public build:"
    echo "$LEAK"
    FAIL=1
  else
    echo "PASS leak-guard (enterprise/ physically empty of source)"
  fi

  # With a git index available, the only tracked entry under enterprise
  # must be the gitlink itself (mode 160000) — no blobs.
  if [ -d .git ] || git rev-parse --git-dir >/dev/null 2>&1; then
    TRACKED=$(git ls-files enterprise/ 2>/dev/null || true)
    if [ -n "$TRACKED" ]; then
      echo "FAIL leak-guard: tracked files under enterprise/ (must be gitlink only):"
      echo "$TRACKED"
      FAIL=1
    else
      echo "PASS leak-guard (no tracked enterprise blobs)"
    fi
  fi
fi

exit $FAIL
