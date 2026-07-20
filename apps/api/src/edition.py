"""Edition switch — the single place that answers "community or managed?".

This module is the SOLE reader of NOUSVIZ_EDITION. Everything else calls
is_managed() / get_edition(); nothing else may touch os.environ for this
key, or edition checks scatter and recreate the two-codebase drift this
initiative exists to end.

Default is community: a self-hosted install that sets nothing gets the
full community product with zero managed behaviour. The control panel
sets NOUSVIZ_EDITION=managed at provision time via the existing
_env.write_and_reload() path.
"""
from __future__ import annotations

import os

COMMUNITY = "community"
MANAGED = "managed"


def get_edition() -> str:
    value = os.environ.get("NOUSVIZ_EDITION", COMMUNITY).strip().lower()
    return MANAGED if value == MANAGED else COMMUNITY


def is_managed() -> bool:
    return get_edition() == MANAGED
