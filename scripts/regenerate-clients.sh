#!/usr/bin/env bash
# B246: regenerate the TypeScript and Python client SDKs from the live
# /openapi.json spec. Idempotent — running twice produces no diff.
#
# Run from repo root:
#   ./scripts/regenerate-clients.sh
#
# Updates packages/client-ts/src/generated/ and
# packages/client-py/nousviz_client/ in place. Bumps the two client
# packages and the web app to match the platform VERSION file (D12).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VERSION="$(cat VERSION | tr -d '[:space:]')"
echo "▶ Regenerating clients for v${VERSION}"

# 1. Dump the live spec to a temp file via the API's openapi() method.
#    This avoids needing a running server — we use the Python app directly.
SPEC_FILE="$(mktemp -t openapi-spec-XXXXXX.json)"
trap 'rm -f "$SPEC_FILE"' EXIT

.venv/bin/python -c "
import json, sys
sys.path.insert(0, '.')
from apps.api.src.main import app
print(json.dumps(app.openapi(), separators=(',', ':')))
" 2>/dev/null > "$SPEC_FILE"

if [ ! -s "$SPEC_FILE" ]; then
  echo "  ✗ Failed to dump spec — is the .venv set up? Run pip install -e sdk/" >&2
  exit 1
fi
SPEC_BYTES=$(wc -c < "$SPEC_FILE" | tr -d ' ')
echo "  ✓ Spec dumped (${SPEC_BYTES} bytes)"

# 2. TypeScript: openapi-typescript-codegen.
echo "▶ Regenerating TypeScript client..."
TS_OUT="packages/client-ts/src/generated"
rm -rf "$TS_OUT"
mkdir -p "$TS_OUT"
npx --yes openapi-typescript-codegen@0.29.0 \
  --input "$SPEC_FILE" \
  --output "$TS_OUT" \
  --client fetch \
  --useOptions \
  >/dev/null 2>&1
echo "  ✓ TS client regenerated → $TS_OUT"

# 3. Python: openapi-python-client.
echo "▶ Regenerating Python client..."
PY_OUT="packages/client-py/nousviz_client"
PY_TMP="$(mktemp -d -t py-client-XXXXXX)"
trap 'rm -f "$SPEC_FILE"; rm -rf "$PY_TMP"' EXIT
PATH="$REPO_ROOT/.venv/bin:$PATH" .venv/bin/openapi-python-client generate \
  --path "$SPEC_FILE" \
  --meta setup \
  --config packages/client-py/openapi-python-client.yaml \
  --output-path "$PY_TMP/out" \
  >/dev/null 2>&1 || {
    # Generator emits warnings on non-JSON content types but still produces output;
    # check the output dir directly.
    if [ ! -d "$PY_TMP/out/nousviz_client" ]; then
      echo "  ✗ Python generator produced no output" >&2
      exit 1
    fi
  }
rm -rf "$PY_OUT"
mv "$PY_TMP/out/nousviz_client" "$PY_OUT"
echo "  ✓ Python client regenerated → $PY_OUT"

# 4. Bump versions in both package manifests to match VERSION.
echo "▶ Pinning package versions to ${VERSION}"
# package.json (TS)
.venv/bin/python -c "
import json, pathlib
p = pathlib.Path('packages/client-ts/package.json')
data = json.loads(p.read_text())
data['version'] = '${VERSION}'
p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
"
echo "  ✓ packages/client-ts/package.json → ${VERSION}"

# package.json (web app) — D12 (v0.9.11.3): keep web app version
# in sync so the apps/web/package.json drift can't recur.
# ensure_ascii=False preserves unicode literals (em-dashes etc.) — without
# this, json.dumps escapes them and re-running the script produces a diff.
.venv/bin/python -c "
import json, pathlib
p = pathlib.Path('apps/web/package.json')
data = json.loads(p.read_text())
data['version'] = '${VERSION}'
p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
"
echo "  ✓ apps/web/package.json → ${VERSION}"

# pyproject.toml (Py) — line-replace (sed-portable, no in-place arg).
.venv/bin/python -c "
import re, pathlib
p = pathlib.Path('packages/client-py/pyproject.toml')
src = p.read_text()
new = re.sub(r'^version\\s*=\\s*\"[^\"]+\"', f'version = \"${VERSION}\"', src, count=1, flags=re.M)
p.write_text(new)
"
echo "  ✓ packages/client-py/pyproject.toml → ${VERSION}"

# 5. Summary
echo ""
echo "▶ Summary"
TS_SERVICES=$(ls "$TS_OUT/services" 2>/dev/null | wc -l | tr -d ' ')
TS_MODELS=$(ls "$TS_OUT/models" 2>/dev/null | wc -l | tr -d ' ')
PY_API_DIRS=$(ls -d "$PY_OUT"/api/*/ 2>/dev/null | wc -l | tr -d ' ')
PY_MODELS=$(ls "$PY_OUT/models" 2>/dev/null | wc -l | tr -d ' ')
echo "  TS:  $TS_SERVICES services, $TS_MODELS models"
echo "  Py:  $PY_API_DIRS api modules, $PY_MODELS model files"
echo ""
echo "  ✓ Done. Verify with:"
echo "    cd packages/client-ts && npm run build"
echo "    cd packages/client-py && python -m build --wheel"
