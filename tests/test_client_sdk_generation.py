"""B246 (v0.9.10.5): verify the regenerate script is idempotent.

Re-runs `scripts/regenerate-clients.sh` in a way that doesn't modify
the live tree (it writes to the live tree, but we restore it from git
afterwards). Asserts that the generated source is byte-identical
between the committed state and a fresh regeneration.

Drift here means either:
- The spec changed without a regeneration step (developer forgot to
  re-run the script), OR
- The generator emits non-deterministic output (would be a bug worth
  filing upstream).

The script is slow (10–30s) because it runs `npx` and the Python
generator. Marked with `@pytest.mark.slow` so contributors can skip
it locally with `-m "not slow"` and only run it in CI / before merge.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TS_OUT = REPO / "packages" / "client-ts" / "src" / "generated"
PY_OUT = REPO / "packages" / "client-py" / "nousviz_client"


def _hash_tree(root: Path) -> str:
    """SHA-256 of all files under root, sorted by path."""
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        # Skip ephemeral / generator-noise files.
        if p.name in ("__pycache__",) or "__pycache__" in p.parts:
            continue
        rel = p.relative_to(root).as_posix()
        h.update(rel.encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


@pytest.mark.slow
def test_regenerate_clients_is_idempotent():
    """Run the regen script and confirm no diff in generated output.

    Restores the working tree from git afterwards so the test is
    side-effect-free — the regen script writes to the live tree, but
    we only care whether a fresh regeneration matches the committed
    state.
    """
    if shutil.which("npx") is None:
        pytest.skip("npx not on PATH — skip generation test")
    if shutil.which("git") is None:
        pytest.skip("git not on PATH — can't restore tree")

    script = REPO / "scripts" / "regenerate-clients.sh"
    if not script.exists():
        pytest.fail("scripts/regenerate-clients.sh missing")

    # Snapshot current state of generated trees.
    ts_before = _hash_tree(TS_OUT)
    py_before = _hash_tree(PY_OUT)

    try:
        # Run the regenerator. Inherits PATH from the test environment.
        result = subprocess.run(
            ["bash", str(script)],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ},
        )
        assert result.returncode == 0, (
            f"regenerate-clients.sh failed:\n--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )

        ts_after = _hash_tree(TS_OUT)
        py_after = _hash_tree(PY_OUT)

        assert ts_before == ts_after, (
            f"TS client regeneration is not idempotent. "
            f"Hash changed: {ts_before[:12]} → {ts_after[:12]}. "
            f"Either the spec drifted from the committed snapshot, or the "
            f"generator emits non-deterministic output."
        )
        assert py_before == py_after, (
            f"Python client regeneration is not idempotent. "
            f"Hash changed: {py_before[:12]} → {py_after[:12]}."
        )
    finally:
        # Restore the live tree from git, regardless of test outcome.
        # This keeps subsequent test runs clean and prevents the test
        # from leaving stale generator output in the working tree if
        # the assertion fails.
        for path in (
            "packages/client-ts/src/generated",
            "packages/client-ts/package.json",
            "packages/client-py/nousviz_client",
            "packages/client-py/pyproject.toml",
        ):
            subprocess.run(
                ["git", "checkout", "--", path],
                cwd=REPO,
                capture_output=True,
                check=False,
            )
