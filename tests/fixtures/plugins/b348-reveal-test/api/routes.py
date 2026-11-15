"""B348 test fixture routes.

`CALLS` records every handler invocation so tests can prove that a request
refused by core (401 / 403) never reaches the plugin.
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/plugins/b348-reveal-test")

FIXED_SECRET = "b348-fixed-secret"
CALLS: list[str] = []


@router.get("/status")
def status():
    CALLS.append("status")
    return {"ok": True}


@router.post("/secret/reveal")
def reveal_secret():
    CALLS.append("secret/reveal")
    return {"value": FIXED_SECRET}


@router.post("/accounts/{account_id}/reveal")
def reveal_account(account_id: str):
    CALLS.append(f"accounts/{account_id}/reveal")
    if account_id == "missing":
        raise HTTPException(404, "No such account")
    return {"account_id": account_id, "value": FIXED_SECRET}


@router.post("/settings/check")
def settings_check():
    CALLS.append("settings/check")
    return {"ok": True}
