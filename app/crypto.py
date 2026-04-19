"""Symmetric encryption for sensitive account fields (e.g. IG password)."""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.settings import settings

# Derive a 32-byte Fernet key from the existing secret_key
_key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
_fernet = Fernet(_key)


def encrypt(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode()).decode()
