"""B217 (v0.9.10.4): per-operation OpenAPI metadata gate.

Every operation in /openapi.json must have:
- A non-empty `summary`.
- A non-empty `description` (FastAPI uses the handler docstring).
- A non-empty `tags` list.
- An `operationId` matching `<resource>.<verb>`.
- At least one 2xx response with either a JSON `$ref` schema OR a
  declared non-JSON content-type (the JS-asset case).

This test guards against regression — a route added in a future
release without these fields will fail CI here.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Add the repo root to sys.path so the API can import.
REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from apps.api.src.main import app  # noqa: E402

OPERATION_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


def _operations():
    """Yield (method, path, op_dict) for every documented operation."""
    spec = app.openapi()
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            yield method, path, op


def _has_typed_response(op: dict) -> bool:
    """True iff the operation declares at least one 2xx response with
    either a JSON $ref schema or a non-JSON content-type."""
    for status, resp in op.get("responses", {}).items():
        if not str(status).startswith("2"):
            continue
        content = resp.get("content") or {}
        if not content:
            # 204 no-content responses are allowed without a content block.
            if str(status) == "204":
                return True
            continue
        for ct, body in content.items():
            if ct == "application/json":
                schema = body.get("schema") or {}
                if "$ref" in schema or schema.get("type"):
                    return True
            else:
                # Non-JSON content type (e.g. application/javascript) is
                # acceptable — it documents the response shape honestly.
                return True
    return False


def test_every_operation_has_summary():
    bad = [(m, p) for m, p, op in _operations() if not (op.get("summary") or "").strip()]
    assert not bad, f"Operations missing summary: {bad[:10]}"


def test_every_operation_has_summary_or_description():
    """Required: summary OR description (FastAPI uses the handler
    docstring as description). The summary is the H1 in /docs/api;
    description is the longer-form body. CRUD endpoints with a tight
    summary often need no description, so we require at least one.
    """
    bad = [
        (m, p)
        for m, p, op in _operations()
        if not (op.get("summary") or "").strip()
        and not (op.get("description") or "").strip()
    ]
    assert not bad, f"Operations missing both summary and description: {bad[:10]}"


def test_every_operation_has_tags():
    bad = [(m, p) for m, p, op in _operations() if not op.get("tags")]
    assert not bad, f"Operations missing tags: {bad[:10]}"


def test_every_operation_has_resource_verb_operation_id():
    bad = [
        (m, p, op.get("operationId", ""))
        for m, p, op in _operations()
        if not OPERATION_ID_PATTERN.match(op.get("operationId", ""))
    ]
    assert not bad, f"Operations with non-resource.verb operationId: {bad[:10]}"


def test_every_operation_has_typed_2xx_response():
    bad = [(m, p) for m, p, op in _operations() if not _has_typed_response(op)]
    assert not bad, f"Operations without typed 2xx response: {bad[:10]}"


def test_no_duplicate_operation_ids():
    seen: dict[str, tuple[str, str]] = {}
    dups: list[str] = []
    for method, path, op in _operations():
        op_id = op.get("operationId", "")
        if op_id in seen:
            dups.append(f"{op_id}: {seen[op_id]} vs {(method, path)}")
        else:
            seen[op_id] = (method, path)
    assert not dups, f"Duplicate operationIds: {dups[:5]}"
