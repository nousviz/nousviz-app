"""B217 (v0.9.10.4): OpenAPI stability snapshot.

The live `/openapi.json` is captured in
`tests/fixtures/openapi-snapshot.json` (info.version stripped to keep
the fixture stable across releases). Any drift requires updating the
fixture deliberately — making spec changes PR-reviewable.

To regenerate after an intentional spec change:

    .venv/bin/python -c "
    import json, sys
    sys.path.insert(0, '.')
    from apps.api.src.main import app
    from pathlib import Path
    spec = app.openapi()
    spec['info']['version'] = '<volatile>'
    Path('tests/fixtures/openapi-snapshot.json').write_text(
        json.dumps(spec, indent=2, sort_keys=True)
    )
    "

Then commit the fixture change in the same PR as the spec change.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from apps.api.src.main import app  # noqa: E402

SNAPSHOT_PATH = REPO / "tests" / "fixtures" / "openapi-snapshot.json"


def _live_spec_normalized() -> dict:
    spec = app.openapi()
    # Strip volatile fields.
    spec.setdefault("info", {})["version"] = "<volatile>"
    return spec


def test_snapshot_exists():
    assert SNAPSHOT_PATH.exists(), (
        f"Missing snapshot: {SNAPSHOT_PATH.relative_to(REPO)}. "
        "Generate it with the snippet in this test's docstring."
    )


def test_openapi_matches_snapshot():
    """Diffs the live spec against the committed snapshot.

    Failure means the spec drifted. If the change is intentional,
    regenerate the snapshot (see this module's docstring) and
    re-commit.
    """
    live = json.loads(json.dumps(_live_spec_normalized(), sort_keys=True))
    snapshot = json.loads(SNAPSHOT_PATH.read_text())

    # Compare the path-set first — fastest signal for added/removed routes.
    live_paths = set(live.get("paths", {}).keys())
    snap_paths = set(snapshot.get("paths", {}).keys())
    added = live_paths - snap_paths
    removed = snap_paths - live_paths
    assert not added and not removed, (
        f"Path drift — added: {sorted(added)[:5]}, removed: {sorted(removed)[:5]}. "
        "Regenerate tests/fixtures/openapi-snapshot.json."
    )

    # Compare each path's operationIds.
    drifted_ops: list[str] = []
    for path in sorted(live_paths):
        live_methods = set(live["paths"][path].keys())
        snap_methods = set(snapshot["paths"][path].keys())
        if live_methods != snap_methods:
            drifted_ops.append(f"{path}: methods {live_methods} vs {snap_methods}")
            continue
        for method in live_methods:
            live_id = live["paths"][path][method].get("operationId")
            snap_id = snapshot["paths"][path][method].get("operationId")
            if live_id != snap_id:
                drifted_ops.append(f"{method.upper()} {path}: {live_id} vs {snap_id}")
    assert not drifted_ops, (
        f"operationId drift: {drifted_ops[:5]}. "
        "Regenerate tests/fixtures/openapi-snapshot.json."
    )

    # Schema name set — added/removed component schemas are reviewable.
    live_schemas = set((live.get("components") or {}).get("schemas", {}).keys())
    snap_schemas = set((snapshot.get("components") or {}).get("schemas", {}).keys())
    added_s = live_schemas - snap_schemas
    removed_s = snap_schemas - live_schemas
    assert not added_s and not removed_s, (
        f"Schema drift — added: {sorted(added_s)[:5]}, removed: {sorted(removed_s)[:5]}. "
        "Regenerate tests/fixtures/openapi-snapshot.json."
    )
