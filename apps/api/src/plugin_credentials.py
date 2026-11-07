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
from typing import Iterable, Optional

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
      1. Encrypted DB (credentials table) — one credential read and
         decrypted; usage recorded under `performed_by` (B342).
      2. Env var fallback (os.environ)

    Returns None if not found in either location.
    """
    # 1. Try encrypted DB
    value = read_plugin_credentials(plugin_id, [field_name], accessor=performed_by).get(field_name)
    if value is not None:
        return value

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


def read_plugin_credentials(
    plugin_id: str,
    keys: Optional[Iterable[str]] = None,
    *,
    accessor: str,
    last_used_by: Optional[str] = None,
    fetch_detail: Optional[str] = None,
) -> dict[str, str]:
    """B342 (v1.0.8): decrypt the plugin's credentials named in `keys`
    (every one when `keys` is None) in one query.

    Only the rows asked for are read and decrypted, so the cost no longer
    grows with how many credentials the plugin holds. Usage telemetry
    (`credential_usage.record_reads`) counts one read per credential
    returned under `accessor`; when `fetch_detail` is given, one `fetch`
    row is added to `credential_audit_log` for the whole request. A
    credential that fails to decrypt is skipped and recorded as
    `decrypt_failed`. Never raises: on a database error, logs and returns {}.
    """
    from .credential_usage import record_event, record_reads

    wanted: Optional[list[str]] = None
    if keys is not None:
        wanted = sorted({str(k) for k in keys if k})
        if not wanted:
            return {}
    conn_name = f"plugin:{plugin_id}"
    out: dict[str, str] = {}
    read_ids: list[str] = []
    failed: list[tuple[str, str]] = []
    connection_id: Optional[str] = None
    try:
        with get_pg_conn() as conn:
            cur = conn.cursor()
            sql = """
                SELECT c.id, c.name, c.encrypted_value, c.nonce, cn.id
                FROM credentials c
                JOIN connections cn ON c.connection_id = cn.id
                WHERE cn.name = %s
            """
            params: list = [conn_name]
            if wanted is not None:
                sql += " AND c.name = ANY(%s)"
                params.append(wanted)
            cur.execute(sql, params)
            rows = cur.fetchall()
            if not rows and fetch_detail:
                cur.execute("SELECT id FROM connections WHERE name = %s", (conn_name,))
                found = cur.fetchone()
                connection_id = str(found[0]) if found else None
    except Exception as exc:
        logger.error(
            "read_plugin_credentials failed for %s: %s",
            plugin_id, exc,
            exc_info=True,
            extra={"plugin_id": plugin_id},
        )
        return {}

    for cred_id, field_name, encrypted_value, nonce, conn_id in rows:
        connection_id = str(conn_id)
        try:
            out[field_name] = _decrypt(bytes(encrypted_value), bytes(nonce))
            read_ids.append(str(cred_id))
        except Exception as exc:
            logger.warning(
                "credential decrypt failed for %s/%s: %s",
                plugin_id, field_name, exc,
                extra={"plugin_id": plugin_id},
            )
            failed.append((str(cred_id), field_name))

    record_reads(read_ids, accessor, last_used_by, plugin_id=plugin_id)
    for cred_id, field_name in failed:
        record_event(connection_id, "decrypt_failed", last_used_by or accessor,
                     f"plugin={plugin_id} field={field_name}", credential_id=cred_id, plugin_id=plugin_id)
    if fetch_detail:
        scope = "full" if wanted is None else f"keys={len(wanted)}"
        record_event(connection_id, "fetch", last_used_by or accessor,
                     f"{fetch_detail} plugin={plugin_id} scope={scope} returned={len(out)}",
                     plugin_id=plugin_id)
    return out


def list_plugin_credentials_decrypted(
    plugin_id: str,
    keys: Optional[Iterable[str]] = None,
    *,
    accessor: Optional[str] = None,
    last_used_by: Optional[str] = None,
    fetch_detail: Optional[str] = None,
) -> dict[str, str]:
    """P208 (v0.9.0), scoped in B342: the plugin's credentials as
    {field_name: plaintext} — all of them, or only `keys`.

    Kept for the broker and the API resolver; see `read_plugin_credentials`.
    Before B342 this decrypted every credential and wrote one audit row per
    credential on every call.
    """
    return read_plugin_credentials(
        plugin_id, keys,
        accessor=accessor or f"bulk:{plugin_id}",
        last_used_by=last_used_by,
        fetch_detail=fetch_detail,
    )


# inject_plugin_credentials removed in v0.9.2 (B135). The legacy v0.8.x
# env-injection path was replaced by the credential broker in v0.9.0
# (P208) — decrypted credentials no longer reach plugin subprocesses via
# os.environ. Plugin code uses nousviz_sdk.get_credential() / get_pg_conn()
# which fetch over the Unix socket broker (subprocess context) or via
# the in-process resolver (API context).
