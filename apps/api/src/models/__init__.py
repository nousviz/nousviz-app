"""B215 (v0.9.10.2): typed response models for the top 50 operator-facing
routes.

Each domain gets its own file (auth.py, plugins.py, jobs.py, etc.).
Models declare the shape FastAPI emits in /openapi.json so operators
reading /docs/api see actual schemas instead of "no schema declared."

Per-route inline models live in their route files when one-off and small;
shared shapes live here when reused across endpoints.

This package is a pure declaration layer — no business logic, no DB
access. Models import only from `pydantic` and stdlib.
"""

from ._errors import ErrorDetail, RBACErrorDetail, StepUpRequiredDetail

__all__ = ["ErrorDetail", "RBACErrorDetail", "StepUpRequiredDetail"]
