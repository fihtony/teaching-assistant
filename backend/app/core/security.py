"""
Security utilities for encryption and decryption.
"""

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Default salt for key derivation (in production, this should be stored securely)
DEFAULT_SALT = b"teaching_app_salt_2024"

# Default teacher ID for development (should be replaced with actual auth in production)
DEFAULT_TEACHER_ID = 1


def get_current_teacher_id() -> int:
    """
    Get the current teacher ID from the session or authentication.

    In production, this would extract the teacher ID from a JWT token
    or session. For now, returns the default teacher ID.

    Returns:
        Teacher ID.
    """
    # TODO: Implement proper authentication
    # For now, return default teacher ID or check environment variable
    return int(os.environ.get("TEACHER_ID", str(DEFAULT_TEACHER_ID)))


def get_encryption_key(password: Optional[str] = None) -> bytes:
    """
    Generate an encryption key from a password or environment variable.

    Args:
        password: Optional password to derive key from. If None, uses environment variable.

    Returns:
        Encryption key bytes.
    """
    if password is None:
        password = os.environ.get(
            "TEACHING_ENCRYPTION_KEY", "default_key_for_local_use"
        )

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=DEFAULT_SALT,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def encrypt_api_key(api_key: str, password: Optional[str] = None) -> str:
    """
    Encrypt an API key for secure storage.

    Args:
        api_key: The API key to encrypt.
        password: Optional password for encryption.

    Returns:
        Encrypted API key as a base64-encoded string.
    """
    key = get_encryption_key(password)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(api_key.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_api_key(encrypted_key: str, password: Optional[str] = None) -> str:
    """
    Decrypt an encrypted API key.

    Args:
        encrypted_key: The encrypted API key (base64-encoded).
        password: Optional password for decryption.

    Returns:
        Decrypted API key.
    """
    key = get_encryption_key(password)
    fernet = Fernet(key)
    encrypted_bytes = base64.urlsafe_b64decode(encrypted_key.encode())
    decrypted = fernet.decrypt(encrypted_bytes)
    return decrypted.decode()
