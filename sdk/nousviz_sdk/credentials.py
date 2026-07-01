"""
Credential accessor for NousViz plugins (P208 / v0.9.0).

Usage:
    from nousviz_sdk import get_credential

    password = get_credential("my-plugin", "password")
    # Returns the decrypted value, or None if no such credential is saved.

# How it works

The NousViz jobs-worker decrypts credentials in its own process (where
the encryption key lives) and serves them to plugin subprocesses over
a Unix domain socket using one-shot authentication tokens. Decrypted
secrets never enter `os.environ`, never appear in `/proc/<pid>/environ`,
and never touch `.env` on disk.

The first call to `get_credential()` triggers a single fetch from the
broker; the response is cached for the subprocess's lifetime. Plugin
authors don't need to manage the connection — just call the function.

# Failure modes

- `CredentialBrokerUnavailable` — raised if the subprocess is running
  outside a NousViz context (no broker socket env set). Typically
  happens when a developer runs `python sync.py` manually. Use the
  NousViz dev harness (shipping in v0.9.3) for local testing.
- `CredentialBrokerError` — raised if the broker denies the request
  (token expired, plugin mismatch) or if a DB read fails. Includes
  the broker's reason in the exception message.

# Why not env vars

Prior to v0.9.0, decrypted credentials were delivered via `os.environ`.
That made them readable by anyone with ptrace access, included in crash
dumps, and prone to accidental logging. The broker model moves the
boundary: decryption happens in the worker, delivery is auditable, and
the subprocess only ever sees plaintext in its own process memory.
"""

from __future__ import annotations

import logging

from ._broker_client import (
    get_cached,
    store as _store,
    CredentialBrokerUnavailable,
    CredentialBrokerError,
)

logger = logging.getLogger("nousviz_sdk.credentials")


def get_credential(plugin_id: str, key: str, env_prefix: str | None = None) -> str | None:
    """
    Retrieve a credential value for this plugin's current subprocess.

    Args:
        plugin_id: Your plugin's declared id (e.g., "example-mysql").
                   Currently informational — the broker knows which
                   plugin is calling via NOUSVIZ_PLUGIN_ID env.
        key: Field name from your connections.fields block (e.g., "password").
        env_prefix: Ignored as of v0.9.0. Kept in the signature for
                    backward compatibility with v0.8.6.x callers. The
                    broker delivers credentials keyed by field_name
                    (same as how they're stored).

    Returns:
        The credential value as a string, or None if the credential
        was not saved for this plugin.

    Raises:
        CredentialBrokerUnavailable: subprocess not spawned by NousViz.
        CredentialBrokerError: broker denied the request or failed to
                               read the credential.
    """
    del env_prefix  # unused — documented above
    creds = get_cached(plugin_id=plugin_id)
    value = creds.get(key)
    if value is None:
        logger.debug(
            f"get_credential: {plugin_id}/{key} not set — "
            f"check the plugin's connections form in the UI."
        )
    return value


def store_credential(
    plugin_id: str,
    field_name: str,
    plaintext: str,
    credential_type: str = "oauth2",
) -> None:
    """Persist an encrypted credential for this plugin (B308, v0.6.8).

    The complement to :func:`get_credential`. Use it when a plugin
    **route handler** captures a secret it must store — most commonly an
    OAuth access/refresh token exchanged in-route, where the provider
    can't redirect through core's ``/api/oauth/callback/<slug>`` (e.g. a
    device / paste-back-code flow). Core encrypts and writes the value via
    the same privileged path the operator Settings form uses; it never
    lands anywhere the ``nousviz_plugin`` role can read raw.

    Args:
        plugin_id: Your plugin's declared id (e.g., "nousviz-agent").
        field_name: The credential key. May be namespaced for per-user
            storage — e.g. ``f"access_token:{user_id}"`` — since the
            underlying store keys on an arbitrary name. Read it back with
            ``get_credential(plugin_id, field_name)``.
        plaintext: The secret value to encrypt and store. Upserts.
        credential_type: Audit-trail classification. Defaults to
            ``"oauth2"``; use ``"api_key"`` / ``"api_token"`` as fitting.

    Raises:
        CredentialBrokerUnavailable: called outside api-process (plugin
            route) context — e.g. from a worker-spawned sync subprocess,
            which can read credentials but not store them.

    Note:
        Available only from plugin **route** handlers (api-process). Sync
        scripts and hooks run in subprocesses that read credentials but
        do not mint them, so this raises there by design.
    """
    _store(plugin_id, field_name, plaintext, credential_type)


__all__ = [
    "get_credential",
    "store_credential",
    "CredentialBrokerUnavailable",
    "CredentialBrokerError",
]
