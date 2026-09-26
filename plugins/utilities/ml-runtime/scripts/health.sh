#!/usr/bin/env bash
# ML runtime health check — returns JSON on stdout.
#
# Reports the installed versions, and whether they match requirements.txt.
# A mismatch is the usual sign that someone upgraded the venv by hand or
# rebuilt it without reinstalling this utility.

source "$(dirname "$0")/_python.sh"

if [ -z "$PY" ]; then
  echo '{"ok": false, "error": "No Python interpreter found"}'
  exit 1
fi

"$PY" - "$REQUIREMENTS" <<'EOF'
import importlib.metadata as md
import json
import sys

pins = {}
for line in open(sys.argv[1]):
    line = line.split("#", 1)[0].strip()
    if "==" in line:
        name, ver = line.split("==", 1)
        pins[name.strip()] = ver.strip()

installed, missing, drift = {}, [], []
for name, want in pins.items():
    try:
        have = md.version(name)
    except md.PackageNotFoundError:
        missing.append(name)
        continue
    installed[name] = have
    if have != want:
        drift.append(f"{name} {have} (pinned {want})")

try:
    import lightgbm  # noqa: F401  (catches a missing OpenMP runtime)
except Exception as e:  # noqa: BLE001
    missing.append(f"lightgbm import failed: {str(e)[:120]}")

out = {"ok": not missing,
       "version": installed.get("lightgbm", "missing"),
       "libraries": installed}
if missing:
    out["error"] = ("Missing: " + ", ".join(missing)
                    + ". Reinstall the ML Runtime utility.")
if drift:
    out["warning"] = "Version differs from pin: " + "; ".join(drift)
print(json.dumps(out))
sys.exit(0 if out["ok"] else 1)
EOF
