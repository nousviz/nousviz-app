#!/usr/bin/env bash
set -euo pipefail

# ML runtime utility — install hook.
#
# The platform has already pip-installed requirements.txt into the running
# venv (B306) by the time this runs. This hook does not install anything
# itself; it proves the result works, because the platform's pip step can
# fail without failing the install (it reports deps_installed: false), and
# LightGBM can install cleanly yet fail to import on a host without the
# OpenMP runtime. Either way the operator gets a clear message and the
# exact command to fix it, instead of a sync job failing weeks later.

source "$(dirname "$0")/_python.sh"

echo "Checking ML runtime libraries..."

if [ -z "$PY" ]; then
  echo "ERROR: no Python interpreter found (looked for $NOUSVIZ_DIR/.venv/bin/python3)." >&2
  exit 1
fi

# Disk: the wheels are already on disk if pip succeeded; this catches the
# case where pip failed for lack of space.
AVAIL_MB=$(df -Pm "$NOUSVIZ_DIR" | awk 'NR==2 {print $4}')
if [ "${AVAIL_MB:-0}" -lt 200 ]; then
  echo "WARNING: only ${AVAIL_MB} MB free under $NOUSVIZ_DIR." >&2
fi

if ! OUT=$("$PY" - <<'EOF' 2>&1
import importlib.metadata as md
import lightgbm, numpy, sklearn  # noqa: F401  (import proves libgomp is present)
for pkg in ("lightgbm", "numpy", "scikit-learn", "scipy"):
    print(f"  {pkg} {md.version(pkg)}")
EOF
); then
  echo "ERROR: the ML libraries did not import with $PY:" >&2
  echo "$OUT" | tail -5 >&2
  if echo "$OUT" | grep -q "libgomp"; then
    echo >&2
    echo "LightGBM needs the OpenMP runtime. Install it, then reinstall this utility:" >&2
    echo "  Debian/Ubuntu:  sudo apt-get install -y libgomp1" >&2
    echo "  RHEL/Fedora:    sudo dnf install -y libgomp" >&2
  else
    echo >&2
    echo "Install the libraries by hand, then reinstall this utility:" >&2
    echo "  $PY -m pip install -r $REQUIREMENTS" >&2
  fi
  exit 1
fi

echo "$OUT"
echo "ML runtime ready."
