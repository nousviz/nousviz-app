"""
Connection and credential models for NousViz.

Connections represent external data sources (APIs, databases).
Credentials are encrypted API keys/tokens stored in Postgres.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ConnectionStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    PENDING = "pending"


class CredentialType(Enum):
    API_KEY = "api_key"
    API_TOKEN = "api_token"
    OAUTH2 = "oauth2"
    BASIC_AUTH = "basic_auth"
    DATABASE = "database"


@dataclass
class Credential:
    """A single encrypted credential (API key, token, password, etc.)"""

    id: str
    connection_id: str
    name: str  # e.g. "cloudflare_api_token", "db_password"
    credential_type: CredentialType
    encrypted_value: bytes  # AES-256-GCM encrypted
    nonce: bytes  # Unique per encryption operation

    # Audit & lifecycle
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_rotated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    last_used_by: Optional[str] = None  # e.g. "sync_cf.py"

    # Staleness
    rotation_reminder_days: Optional[int] = 365  # Warn after this many days

    @property
    def days_since_rotation(self) -> int:
        """Days since the key was last rotated (or created if never rotated)."""
        ref = self.last_rotated_at or self.created_at
        return (datetime.now(timezone.utc) - ref).days

    @property
    def is_stale(self) -> bool:
        """True if the key hasn't been rotated within the reminder period."""
        if self.rotation_reminder_days is None:
            return False
        return self.days_since_rotation > self.rotation_reminder_days

    @property
    def masked_value_hint(self) -> str:
        """For UI display — never expose the real value to the browser."""
        return "••••••••"

    def to_dict(self) -> dict:
        """Safe serialization for API responses — never includes the encrypted value."""
        return {
            "id": self.id,
            "connection_id": self.connection_id,
            "name": self.name,
            "credential_type": self.credential_type.value,
            "created_at": self.created_at.isoformat(),
            "last_rotated_at": self.last_rotated_at.isoformat() if self.last_rotated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "last_used_by": self.last_used_by,
            "days_since_rotation": self.days_since_rotation,
            "is_stale": self.is_stale,
            "rotation_reminder_days": self.rotation_reminder_days,
        }


@dataclass
class Connection:
    """An external data source connection (API, database, etc.)"""

    id: str
    plugin_id: str  # Which plugin owns this connection
    name: str  # User-facing name, e.g. "My Cloudflare Account"
    connection_type: str  # e.g. "cloudflare", "mysql", "quickbooks"
    status: ConnectionStatus = ConnectionStatus.PENDING

    # Health tracking
    last_health_check: Optional[datetime] = None
    last_successful_sync: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    config: dict = field(default_factory=dict)  # Non-secret config (host, port, etc.)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "plugin_id": self.plugin_id,
            "name": self.name,
            "connection_type": self.connection_type,
            "status": self.status.value,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "last_successful_sync": self.last_successful_sync.isoformat() if self.last_successful_sync else None,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "config": self.config,
        }
