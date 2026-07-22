"""Conditional load of the managed-edition add-on (MC-203).

The ONLY place in core that imports `nousviz_enterprise`. Community
boots return before any import happens — the public build passes its
suite with `enterprise/` physically absent (proven by CI, MC-205).

Fail-open: in managed mode, a missing or broken add-on logs loudly and
the instance continues with community behaviour. A customer's boot is
never sacrificed to our packaging mistake.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from . import hooks
from .edition import is_managed

logger = logging.getLogger("nousviz.enterprise")

_PACKAGE = "nousviz_enterprise"
_ENTERPRISE_DIR = Path(__file__).resolve().parents[3] / "enterprise"


def load_enterprise(app) -> bool:
    """Load + register the enterprise add-on. Returns True iff registered."""
    if not is_managed():
        return False

    if _ENTERPRISE_DIR.is_dir() and str(_ENTERPRISE_DIR) not in sys.path:
        sys.path.insert(0, str(_ENTERPRISE_DIR))

    try:
        module = __import__(_PACKAGE)
    except ImportError as exc:
        logger.error(
            "NOUSVIZ_EDITION=managed but the enterprise add-on is not "
            "importable (%s). Continuing with community behaviour — "
            "managed enforcement is NOT active. Check that enterprise/ "
            "is present and the submodule is initialised.",
            exc,
        )
        return False

    try:
        module.register(app=app, hooks=hooks)
    except Exception:
        logger.exception(
            "Enterprise add-on import succeeded but register() failed. "
            "Continuing with community behaviour (fail-open)."
        )
        return False

    logger.info(
        "Enterprise add-on registered (version %s).",
        getattr(module, "__version__", "unknown"),
    )
    return True
