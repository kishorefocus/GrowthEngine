"""
Cryptography service: Fernet-based encrypt/decrypt for OAuth tokens.
NEVER log tokens. Tokens are stored encrypted and decrypted in memory only.
"""
import base64
import os

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


_cached_key: str | None = None


def _get_fernet() -> Fernet:
    """Return a Fernet instance using the configured ENCRYPTION_KEY."""
    global _cached_key
    key = settings.encryption_key
    if not key:
        if not _cached_key:
            _cached_key = Fernet.generate_key().decode()
        key = _cached_key
    # Accept both raw base64url keys and plain strings
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        # Might already be bytes
        return Fernet(key)


def encrypt_token(plaintext: str) -> str:
    """Encrypt a plaintext token. Returns base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a ciphertext token. Raises ValueError on failure."""
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Token decryption failed — invalid or tampered ciphertext.") from exc
