"""
Credential manager for NousViz.

Handles the full lifecycle of connections and credentials:
- Create/update/delete connections
- Store and retrieve encrypted credentials
- Audit logging for all credential operations
- Staleness checks and health monitoring
- Credential hints for debugging (never exposes real values)
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from .models import Connection, Credential, ConnectionStatus, CredentialType
from .encryption import encrypt, decrypt

logger = logging.getLogger(__name__)


class CredentialManager:
    """
    Manages connections and their encrypted credentials.

    All credential values are encrypted before storage and decrypted
    only when a sync job needs them. Decrypted values never touch disk.
    """

    def __init__(self, db):
        """
        Args:
            db: Async database connection (e.g. asyncpg pool)
        """
        self.db = db

    # ── Connections ───────────────────────────────────────────────

    async def create_connection(
        self,
        plugin_id: str,
        name: str,
        connection_type: str,
        config: Optional[dict] = None,
    ) -> Connection:
        """Create a new connection for a plugin."""
        conn_id = str(uuid.uuid4())
        row = await self.db.fetchrow(
            """
            INSERT INTO connections (id, plugin_id, name, connection_type, config)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            conn_id, plugin_id, name, connection_type, config or {},
        )
        logger.info(f"Connection created: {name} ({plugin_id})")
        return self._row_to_connection(row)

    async def get_connection(self, connection_id: str) -> Optional[Connection]:
        row = await self.db.fetchrow(
            "SELECT * FROM connections WHERE id = $1", connection_id
        )
        return self._row_to_connection(row) if row else None

    async def list_connections(self, plugin_id: Optional[str] = None) -> list[Connection]:
        if plugin_id:
            rows = await self.db.fetch(
                "SELECT * FROM connections WHERE plugin_id = $1 ORDER BY created_at", plugin_id
            )
        else:
            rows = await self.db.fetch("SELECT * FROM connections ORDER BY created_at")
        return [self._row_to_connection(r) for r in rows]

    async def update_connection_status(
        self,
        connection_id: str,
        status: ConnectionStatus,
        error: Optional[str] = None,
    ):
        """Update connection health status after a sync or health check."""
        now = datetime.now(timezone.utc)
        if status == ConnectionStatus.CONNECTED:
            await self.db.execute(
                """
                UPDATE connections
                SET status = $2, last_health_check = $3, last_successful_sync = $3,
                    last_error = NULL, consecutive_failures = 0
                WHERE id = $1
                """,
                connection_id, status.value, now,
            )
        else:
            await self.db.execute(
                """
                UPDATE connections
                SET status = $2, last_health_check = $3, last_error = $4,
                    consecutive_failures = consecutive_failures + 1
                WHERE id = $1
                """,
                connection_id, status.value, now, error,
            )

    async def delete_connection(self, connection_id: str):
        """Delete a connection and all its credentials (CASCADE)."""
        await self.db.execute("DELETE FROM connections WHERE id = $1", connection_id)
        logger.info(f"Connection deleted: {connection_id}")

    # ── Credentials ──────────────────────────────────────────────

    async def store_credential(
        self,
        connection_id: str,
        name: str,
        credential_type: CredentialType,
        plaintext_value: str,
        rotation_reminder_days: int = 365,
    ) -> dict:
        """
        Encrypt and store a credential.

        If a credential with the same name already exists for this connection,
        it is rotated (updated) and the rotation timestamp is set.
        """
        encrypted_value, nonce = encrypt(plaintext_value)

        # Check if this is a rotation (credential already exists)
        existing = await self.db.fetchrow(
            "SELECT id FROM credentials WHERE connection_id = $1 AND name = $2",
            connection_id, name,
        )

        now = datetime.now(timezone.utc)

        if existing:
            # Rotation — update existing credential
            await self.db.execute(
                """
                UPDATE credentials
                SET encrypted_value = $3, nonce = $4, last_rotated_at = $5,
                    rotation_reminder_days = $6
                WHERE connection_id = $1 AND name = $2
                """,
                connection_id, name, encrypted_value, nonce, now, rotation_reminder_days,
            )
            await self._audit_log(existing["id"], connection_id, "rotated", "user")
            logger.info(f"Credential rotated: {name} on connection {connection_id}")
        else:
            # New credential
            cred_id = str(uuid.uuid4())
            await self.db.execute(
                """
                INSERT INTO credentials
                    (id, connection_id, name, credential_type, encrypted_value, nonce, rotation_reminder_days)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                cred_id, connection_id, name, credential_type.value,
                encrypted_value, nonce, rotation_reminder_days,
            )
            await self._audit_log(cred_id, connection_id, "created", "user")
            logger.info(f"Credential stored: {name} on connection {connection_id}")

        return {"name": name, "status": "stored"}

    async def get_credential_value(
        self,
        connection_id: str,
        name: str,
        used_by: Optional[str] = None,
    ) -> Optional[str]:
        """
        Decrypt and return a credential value for use by a sync script.

        Updates last_used_at and logs the access. The returned value
        should only be held in memory and passed to the API call.
        """
        row = await self.db.fetchrow(
            "SELECT * FROM credentials WHERE connection_id = $1 AND name = $2",
            connection_id, name,
        )
        if not row:
            return None

        plaintext = decrypt(row["encrypted_value"], row["nonce"])

        # Update usage tracking
        now = datetime.now(timezone.utc)
        await self.db.execute(
            "UPDATE credentials SET last_used_at = $3, last_used_by = $4 WHERE id = $1",
            row["id"], now, now, used_by,
        )
        await self._audit_log(
            row["id"], connection_id, "used", used_by or "system",
            detail=f"Decrypted for sync by {used_by}",
        )

        return plaintext

    async def list_credentials(self, connection_id: str) -> list[dict]:
        """
        List credentials for a connection — metadata only, never values.

        Returns safe dicts with audit info, staleness, and masked hints.
        """
        rows = await self.db.fetch(
            "SELECT * FROM credentials WHERE connection_id = $1 ORDER BY name",
            connection_id,
        )
        results = []
        for row in rows:
            cred = Credential(
                id=str(row["id"]),
                connection_id=str(row["connection_id"]),
                name=row["name"],
                credential_type=CredentialType(row["credential_type"]),
                encrypted_value=row["encrypted_value"],
                nonce=row["nonce"],
                created_at=row["created_at"],
                last_rotated_at=row["last_rotated_at"],
                last_used_at=row["last_used_at"],
                last_used_by=row["last_used_by"],
                rotation_reminder_days=row["rotation_reminder_days"],
            )
            results.append(cred.to_dict())
        return results

    async def delete_credential(self, connection_id: str, name: str):
        """Delete a credential. The encrypted value is wiped from Postgres."""
        row = await self.db.fetchrow(
            "SELECT id FROM credentials WHERE connection_id = $1 AND name = $2",
            connection_id, name,
        )
        if row:
            await self._audit_log(row["id"], connection_id, "deleted", "user")
            await self.db.execute(
                "DELETE FROM credentials WHERE connection_id = $1 AND name = $2",
                connection_id, name,
            )
            logger.info(f"Credential deleted: {name}")

    # ── Staleness & Debugging ────────────────────────────────────

    async def get_stale_credentials(self) -> list[dict]:
        """Find all credentials that haven't been rotated within their reminder period."""
        rows = await self.db.fetch(
            """
            SELECT c.*, conn.name as connection_name, conn.plugin_id
            FROM credentials c
            JOIN connections conn ON c.connection_id = conn.id
            WHERE c.rotation_reminder_days IS NOT NULL
              AND (c.last_rotated_at IS NULL AND c.created_at < now() - (c.rotation_reminder_days || ' days')::interval)
              OR  (c.last_rotated_at IS NOT NULL AND c.last_rotated_at < now() - (c.rotation_reminder_days || ' days')::interval)
            ORDER BY COALESCE(c.last_rotated_at, c.created_at) ASC
            """
        )
        return [
            {
                "credential_name": r["name"],
                "connection_name": r["connection_name"],
                "plugin_id": r["plugin_id"],
                "days_since_rotation": (datetime.now(timezone.utc) - (r["last_rotated_at"] or r["created_at"])).days,
                "last_rotated_at": (r["last_rotated_at"] or r["created_at"]).isoformat(),
            }
            for r in rows
        ]

    async def get_debug_hints(self, connection_id: str) -> list[str]:
        """
        Generate debugging hints when a connection is failing.

        Checks for common issues: stale keys, never-used credentials,
        long gaps since last successful use.
        """
        hints = []
        creds = await self.db.fetch(
            "SELECT * FROM credentials WHERE connection_id = $1", connection_id
        )
        conn = await self.db.fetchrow(
            "SELECT * FROM connections WHERE id = $1", connection_id
        )

        if not creds:
            hints.append("No credentials configured for this connection.")
            return hints

        for cred in creds:
            name = cred["name"]
            created = cred["created_at"]
            rotated = cred["last_rotated_at"]
            last_used = cred["last_used_at"]
            ref_date = rotated or created
            days_old = (datetime.now(timezone.utc) - ref_date).days

            if last_used is None:
                hints.append(f"'{name}' has never been used by a sync. It may be misconfigured.")

            if days_old > 365:
                hints.append(
                    f"'{name}' hasn't been rotated in {days_old} days. "
                    "The API key may have expired — try generating a new one from the provider."
                )
            elif days_old > 180:
                hints.append(
                    f"'{name}' is {days_old} days old. Consider rotating it if syncs are failing."
                )

        if conn and conn["consecutive_failures"] >= 3:
            hints.append(
                f"This connection has failed {conn['consecutive_failures']} times in a row. "
                f"Last error: {conn['last_error'] or 'unknown'}"
            )

        return hints

    # ── Audit Log ────────────────────────────────────────────────

    async def _audit_log(
        self,
        credential_id: str,
        connection_id: str,
        action: str,
        performed_by: str,
        detail: Optional[str] = None,
    ):
        await self.db.execute(
            """
            INSERT INTO credential_audit_log (credential_id, connection_id, action, performed_by, detail)
            VALUES ($1, $2, $3, $4, $5)
            """,
            credential_id, connection_id, action, performed_by, detail,
        )

    async def get_audit_log(
        self,
        connection_id: str,
        limit: int = 50,
    ) -> list[dict]:
        """Get recent audit log entries for a connection."""
        rows = await self.db.fetch(
            """
            SELECT cal.*, c.name as credential_name
            FROM credential_audit_log cal
            JOIN credentials c ON cal.credential_id = c.id
            WHERE cal.connection_id = $1
            ORDER BY cal.created_at DESC
            LIMIT $2
            """,
            connection_id, limit,
        )
        return [
            {
                "credential_name": r["credential_name"],
                "action": r["action"],
                "performed_by": r["performed_by"],
                "detail": r["detail"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _row_to_connection(row) -> Connection:
        return Connection(
            id=str(row["id"]),
            plugin_id=row["plugin_id"],
            name=row["name"],
            connection_type=row["connection_type"],
            status=ConnectionStatus(row["status"]),
            last_health_check=row["last_health_check"],
            last_successful_sync=row["last_successful_sync"],
            last_error=row["last_error"],
            consecutive_failures=row["consecutive_failures"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            config=row["config"],
        )
