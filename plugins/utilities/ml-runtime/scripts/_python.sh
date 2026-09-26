#!/usr/bin/env bash
# Shared by the ML runtime hooks: resolve the Python the platform runs.
#
# The API and the jobs-worker both run from $NOUSVIZ_DIR/.venv (see
# ecosystem.config.js), and the platform pip-installs requirements.txt with
# that interpreter. ML_RUNTIME_PYTHON overrides it for testing.

NOUSVIZ_DIR="${NOUSVIZ_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)}"

if [ -n "${ML_RUNTIME_PYTHON:-}" ]; then
  PY="$ML_RUNTIME_PYTHON"
elif [ -x "$NOUSVIZ_DIR/.venv/bin/python3" ]; then
  PY="$NOUSVIZ_DIR/.venv/bin/python3"
else
  PY="$(command -v python3 || true)"
fi

REQUIREMENTS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/requirements.txt"
