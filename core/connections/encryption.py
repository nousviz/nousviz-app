"""
Credential encryption for NousViz.

Uses AES-256-GCM for authenticated encryption.
The encryption key is derived from an app-level secret stored in
an environment variable — never in the database or code.

Security properties:
- Each credential gets a unique random nonce (no nonce reuse)
- GCM provides both confidentiality and integrity
- Decrypted values only exist in memory, never written to disk/logs
"""

import os
import hashlib
import secrets
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# AES-256-GCM constants
NONCE_SIZE = 12  # 96-bit nonce (GCM standard)
TAG_SIZE = 16  # 128-bit auth tag
KEY_SIZE = 32  # 256-bit key

# Environment variable for the master encryption key
ENV_KEY_NAME = "NOUSVIZ_ENCRYPTION_KEY"


class EncryptionError(Exception):
    pass


def _get_master_key() -> bytes:
    """
    Derive a 256-bit encryption key from the app secret.

    The secret should be a high-entropy string set in the environment.
    We use SHA-256 to normalize it to exactly 32 bytes.
    """
    secret = os.environ.get(ENV_KEY_NAME)
    if not secret:
        raise EncryptionError(
            f"Missing {ENV_KEY_NAME} environment variable. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    if len(secret) < 32:
        raise EncryptionError(
            f"{ENV_KEY_NAME} is too short. Use at least 32 characters."
        )
    return hashlib.sha256(secret.encode()).digest()


def encrypt(plaintext: str) -> Tuple[bytes, bytes]:
    """
    Encrypt a credential value.

    Returns:
        (encrypted_value, nonce) — both should be stored in Postgres.

    The encrypted_value includes the GCM auth tag appended.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise EncryptionError(
            "cryptography package required. Install with: pip install cryptography"
        )

    key = _get_master_key()
    nonce = secrets.token_bytes(NONCE_SIZE)
    aesgcm = AESGCM(key)
    encrypted = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

    # Log the operation, never the value
    logger.info("Credential encrypted successfully")

    return encrypted, nonce


def decrypt(encrypted_value: bytes, nonce: bytes) -> str:
    """
    Decrypt a credential value.

    Returns the plaintext string. This value should only exist in memory
    and be passed directly to the plugin sync function.

    Never log, print, or write the return value.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise EncryptionError(
            "cryptography package required. Install with: pip install cryptography"
        )

    key = _get_master_key()
    aesgcm = AESGCM(key)

    try:
        plaintext = aesgcm.decrypt(nonce, encrypted_value, None)
    except Exception:
        raise EncryptionError(
            "Failed to decrypt credential. The encryption key may have changed, "
            "or the stored data is corrupted."
        )

    logger.info("Credential decrypted for use")
    return plaintext.decode("utf-8")


def generate_app_secret() -> str:
    """Generate a new app-level encryption secret. Run once during setup."""
    return secrets.token_hex(32)
