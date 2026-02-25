"""
API Key encryption/decryption using Fernet symmetric encryption.
Falls back to plaintext storage if ENCRYPTION_KEY is not set (dev mode).
"""
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.terminal_ui import ui


def _get_fernet() -> Fernet | None:
    """Get Fernet instance if encryption key is configured."""
    if not settings.encryption_key:
        return None
    try:
        return Fernet(settings.encryption_key.encode())
    except Exception as e:
        ui.warning(f"Invalid ENCRYPTION_KEY: {e}", "Crypto")
        return None


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key. Returns plaintext if no encryption key configured."""
    if not plaintext:
        return ""
    f = _get_fernet()
    if f is None:
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """Decrypt an API key. Returns as-is if not encrypted or no key configured."""
    if not ciphertext:
        return ""
    f = _get_fernet()
    if f is None:
        return ciphertext
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        # Not encrypted (legacy or dev mode) — return as-is
        return ciphertext


def mask_api_key(key: str) -> str:
    """Mask an API key for display: show first 12 chars + ***"""
    if not key:
        return ""
    if len(key) <= 12:
        return "***"
    return key[:12] + "***"
