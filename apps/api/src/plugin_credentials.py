"""
Plugin credential helpers — encrypted storage and retrieval.

Uses the existing AES-256-GCM encryption from core/connections/encryption.py.
Credentials are stored in the `credentials` table (migration 001), linked
to a connection row in the `connections` table.

Fallback chain: DB (encrypted) → env var (plaintext).
Plugins don't need to change — credentials are injected into os.environ
by the sync runner at runtime.
"""

import logging
import os
import uuid
from typing import Optional

from .db import get_pg_conn

logger = logging.getLogger("nousviz.plugin_credentials")


def _encrypt(plaintext: str) -> tuple[bytes, bytes]:
    """Encrypt a credential value. Returns (ciphertext, nonce)."""
    from core.connections.encryption import encrypt
    return encrypt(plaintext)


def _decrypt(encrypted_value: bytes, nonce: bytes) -> str:
    """Decrypt a credential value. Returns plaintext."""
    from core.connections.encryption import decrypt
    return decrypt(encrypted_value, nonce)


def get_or_create_plugin_connection(plugin_id: str) -> str:
    """
    Get or create a connection row for a plugin.
    Returns the connection UUID.
    """
    with get_pg_conn() as conn:
        cur = conn.cursor()

        # Check if a connection already exists for this plugin
        # Plugin connections use name = "plugin:{plugin_id}" convention
        conn_name = f"plugin:{plugin_id}"
        cur.execute(
            "SELECT id FROM connections WHERE name = %s",
            (conn_name,),
        )
        row = cur.fetchone()
        if row:
            return str(row[0])

        # Create one
        conn_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO connections (id, name, type, config, is_default, is_active)
            VALUES (%s, %s, 'postgres', '{}'::jsonb, false, true)
            RETURNING id
            """,
            (conn_id, conn_name),
        )
        logger.info(
            "Created connection row for plugin %s: %s",
            plugin_id, conn_id,
            extra={"plugin_id": plugin_id},
        )
        return conn_id


def store_plugin_credential(
    plugin_id: str,
    field_name: str,
    plaintext: str,
    credential_type: str = "api_key",
    performed_by: str = "settings_ui",
) -> None:
    """
    Encrypt and store a credential for a plugin.
    Upserts — updates if the field already exists.
    """
    connection_id = get_or_create_plugin_connection(plugin_id)
    encrypted_value, nonce = _encrypt(plaintext)

    with get_pg_conn() as conn:
        cur = conn.cursor()

        # Check if credential exists
        cur.execute(
            "SELECT id FROM credentials WHERE connection_id = %s AND name = %s",
            (connection_id, field_name),
        )
        existing = cur.fetchone()

        if existing:
            # Update (rotation)
            cred_id = str(existing[0])
            cur.execute(
                """
                UPDATE credentials
                SET encrypted_value = %s, nonce = %s, last_rotated_at = now()
                WHERE id = %s
                """,
                (encrypted_value, nonce, cred_id),
            )
            action = "rotated"
        else:
            # Create
            cred_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO credentials (id, connection_id, name, credential_type, encrypted_value, nonce)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (cred_id, connection_id, field_name, credential_type, encrypted_value, nonce),
            )
            action = "created"

        # Audit log
        cur.execute(
            """
            INSERT INTO credential_audit_log (credential_id, connection_id, action, performed_by, detail)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (cred_id, connection_id, action, performed_by, f"plugin={plugin_id} field={field_name}"),
        )

    logger.info(
        "Credential %s: plugin=%s field=%s",
        action, plugin_id, field_name,
        extra={"plugin_id": plugin_id},
    )


def get_plugin_credential(
    plugin_id: str,
    field_name: str,
    env_prefix: str = "",
    performed_by: str = "sync",
) -> Optional[str]:
    """
    Get a decrypted credential for a plugin.

    Lookup chain:
      1. Encrypted DB (credentials table)
      2. Env var fallback (os.environ)

    Returns None if not found in either location.
    """
    # 1. Try encrypted DB
    conn_name = f"plugin:{plugin_id}"
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT c.id, c.encrypted_value, c.nonce
                FROM credentials c
                JOIN connections cn ON c.connection_id = cn.id
                WHERE cn.name = %s AND c.name = %s
                """,
                (conn_name, field_name),
            )
            row = cur.fetchone()

            if row:
                cred_id, encrypted_value, nonce = row
                plaintext = _decrypt(bytes(encrypted_value), bytes(nonce))

                # Update last_used_at and log
                cur.execute(
                    "UPDATE credentials SET last_used_at = now(), last_used_by = %s WHERE id = %s",
                    (performed_by, str(cred_id)),
                )
                cur.execute(
                    """
                    INSERT INTO credential_audit_log (credential_id, connection_id, action, performed_by, detail)
                    SELECT %s, connection_id, 'used', %s, %s
                    FROM credentials WHERE id = %s
                    """,
                    (str(cred_id), performed_by, f"plugin={plugin_id} field={field_name}", str(cred_id)),
                )

                return plaintext
    except Exception as e:
        logger.warning(
            "DB credential lookup failed for %s/%s: %s",
            plugin_id, field_name, e,
            extra={"plugin_id": plugin_id},
        )

    # 2. Fallback: env var
    if env_prefix:
        env_key = f"{env_prefix}{field_name.upper()}"
        val = os.environ.get(env_key)
        if val:
            logger.debug(
                "Credential fallback to env var: %s",
                env_key,
                extra={"plugin_id": plugin_id},
            )
            return val

    return None


def list_plugin_credentials_decrypted(plugin_id: str) -> dict[str, str]:
    """P208 (v0.9.0): bulk-fetch every credential for a plugin, decrypted.

    Used by the credential broker to answer a subprocess's GET in one
    round trip — each handler call decrypts exactly once, returns a
    dict of field_name → plaintext, and the broker serializes to JSON.

    Logs each credential use to credential_audit_log the same way
    `get_plugin_credential` does (one INSERT per field for auditability).
    Any decryption failure on one field does NOT block the others —
    returns an empty value for that field with a warning logged.

    Returns: {field_name: plaintext, ...}. Empty dict if plugin has no
    credentials saved.
    """
    conn_name = f"plugin:{plugin_id}"
    out: dict[str, str] = {}
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT c.id, c.name, c.encrypted_value, c.nonce
                FROM credentials c
                JOIN connections cn ON c.connection_id = cn.id
                WHERE cn.name = %s
                """,
                (conn_name,),
            )
            rows = cur.fetchall()
            for cred_id, field_name, encrypted_value, nonce in rows:
                try:
                    out[field_name] = _decrypt(bytes(encrypted_value), bytes(nonce))
                except Exception as exc:
                    logger.warning(
                        "credential decrypt failed for %s/%s: %s",
                        plugin_id, field_name, exc,
                        extra={"plugin_id": plugin_id},
                    )
                    continue

                # Audit: update last_used + append to credential_audit_log.
                try:
                    cur.execute(
                        "UPDATE credentials SET last_used_at = now(), last_used_by = %s WHERE id = %s",
                        ("credential_broker", str(cred_id)),
                    )
                    cur.execute(
                        """
                        INSERT INTO credential_audit_log (credential_id, connection_id, action, performed_by, detail)
                        SELECT %s, connection_id, 'used', %s, %s
                        FROM credentials WHERE id = %s
                        """,
                        (str(cred_id), "credential_broker", f"broker fetch plugin={plugin_id}", str(cred_id)),
                    )
                except Exception as exc:
                    logger.warning(
                        "credential audit log write failed for %s/%s: %s",
                        plugin_id, field_name, exc,
                        extra={"plugin_id": plugin_id},
                    )
    except Exception as exc:
        logger.error(
            "list_plugin_credentials_decrypted failed for %s: %s",
            plugin_id, exc,
            exc_info=True,
            extra={"plugin_id": plugin_id},
        )
        return {}
    return out


# inject_plugin_credentials removed in v0.9.2 (B135). The legacy v0.8.x
# env-injection path was replaced by the credential broker in v0.9.0
# (P208) — decrypted credentials no longer reach plugin subprocesses via
# os.environ. Plugin code uses nousviz_sdk.get_credential() / get_pg_conn()
# which fetch over the Unix socket broker (subprocess context) or via
# the in-process resolver (API context).
