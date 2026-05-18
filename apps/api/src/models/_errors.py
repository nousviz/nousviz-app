"""B215 (v0.9.10.2): shared error response shapes.

FastAPI's `HTTPException(status, detail)` emits a JSON body of shape
`{"detail": <detail>}`. The detail can be a string or a dict; route
handlers in this codebase use both patterns:

- Plain string detail (most common): `raise HTTPException(401, "Not authenticated")`
- Structured dict detail (B236, B251 conventions): `raise HTTPException(401, {"error": "stepup_required", "message": "..."})`

The schemas here describe both shapes so /openapi.json declares
realistic 4xx response bodies for operators reading the spec.
"""

from __future__ import annotations


from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Generic 4xx response. The `detail` field is a human-readable
    string describing the error (FastAPI's default HTTPException shape).
    """
    detail: str = Field(
        ...,
        description="Human-readable error message.",
        examples=["Not authenticated.", "Plugin 'foo' not found."],
    )


class RBACErrorDetail(BaseModel):
    """403 response from the RBAC layer (B227+). Same `detail` field but
    with a documented format: `Permission denied: this action requires <permission>.`
    """
    detail: str = Field(
        ...,
        description="Permission-deny message naming the required permission.",
        examples=["Permission denied: this action requires plugins.install."],
    )


class StepUpRequiredErrorBody(BaseModel):
    """The structured detail body returned by `requires_step_up` (B236)
    and `PATCH /api/auth/me` with password (B251). Frontend's StepUpController
    keys off `detail.error == 'stepup_required'` to pop the modal."""
    error: str = Field(default="stepup_required", description="Stable machine-readable error code.")
    message: str = Field(..., description="Human-readable explanation.")


class StepUpRequiredDetail(BaseModel):
    """401 response from any endpoint gated by `requires_step_up`.
    The `detail` field is a structured dict, not a string."""
    detail: StepUpRequiredErrorBody
