"""
Shared .env file reader/writer.

Used by settings.py and auth.py (setup/config endpoint) so neither
has to import from the other (which would create a circular import).
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger("nousviz.env")

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE  = REPO_ROOT / ".env"


def _sanitise_env_value(value: str) -> str:
    """Strip newlines and carriage returns to prevent injection of extra env vars."""
    return value.replace("\n", "").replace("\r", "")


def write_env_file(updates: dict[str, str]) -> None:
    """
    Write updated keys into .env, preserving comments and order.
    Keys not already present are appended.
    Values are sanitised to prevent newline injection.
    """
    updates = {k: _sanitise_env_value(v) for k, v in updates.items()}
    if not ENV_FILE.exists():
        lines = [f"{k}={v}" for k, v in updates.items()]
        ENV_FILE.write_text("\n".join(lines) + "\n")
        return

    original = ENV_FILE.read_text().splitlines()
    written: set[str] = set()
    new_lines: list[str] = []

    for line in original:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        if "=" in stripped:
            k = stripped.partition("=")[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}")
                written.add(k)
                continue
        new_lines.append(line)

    for k, v in updates.items():
        if k not in written:
            new_lines.append(f"{k}={v}")

    ENV_FILE.write_text("\n".join(new_lines) + "\n")


def write_and_reload(updates: dict[str, str]) -> None:
    """
    Write .env, patch the current process's os.environ, and schedule a PM2
    reload of the `api` process so sibling gunicorn workers pick up the
    changes (B190).

    The reload runs in a background thread after a short delay so that the
    HTTP response that triggered the update completes before the reload
    truncates the upstream. See B189 for the "upstream prematurely closed"
    failure this avoids.

    Callers should finish sending the response before the 2s delay elapses —
    any handler running in the normal request flow satisfies this naturally.
    """
    write_env_file(updates)
    for k, v in updates.items():
        os.environ[k] = v

    logger.info(
        "ENV_RELOAD_REQUIRED: %s — scheduling pm2 reload api --update-env",
        sorted(updates.keys()),
    )
    _schedule_pm2_reload()


def _schedule_pm2_reload(delay_seconds: float = 2.0) -> None:
    """Kick off `pm2 reload api --update-env` in a daemon thread after a delay."""
    import threading

    def _reload() -> None:
        import subprocess
        import time
        time.sleep(delay_seconds)
        try:
            result = subprocess.run(
                ["pm2", "reload", "api", "--update-env"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                logger.info("pm2 reload api --update-env succeeded")
            else:
                logger.warning(
                    "pm2 reload api --update-env returned %d: %s",
                    result.returncode,
                    (result.stderr or result.stdout or "").strip()[:500],
                )
        except FileNotFoundError:
            # pm2 not installed (local dev without PM2) — that's fine, the
            # handling worker already has the new env from the os.environ patch
            logger.info("pm2 not found — skipping reload (local dev mode)")
        except Exception as exc:
            logger.warning("pm2 reload api failed: %s", exc)

    threading.Thread(target=_reload, daemon=True, name="env-reload").start()
