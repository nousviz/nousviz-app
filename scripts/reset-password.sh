#!/usr/bin/env bash
#
# B251 (v0.9.10.0.3) — Operator-recovery password reset.
#
# Use when:
#   - SMTP isn't configured (so the email-link forgot-password flow doesn't work)
#   - The only superadmin lost their password and there's no other way in
#
# Usage:
#   ./scripts/reset-password.sh <email>
#
# Prompts for a new password (no echo), updates users.password_hash via
# parameterized SQL, kills all active sessions for the user, writes an
# audit row. See apps/api/scripts/reset_password.py for the implementation.

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="$APP_DIR/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Error: project venv not found at $VENV_PYTHON" >&2
    echo "  Run scripts/setup.sh first to create the venv, or activate one manually." >&2
    exit 1
fi

exec "$VENV_PYTHON" "$APP_DIR/apps/api/scripts/reset_password.py" "$@"
