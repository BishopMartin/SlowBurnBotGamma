"""Symmetric encryption for sensitive account fields (e.g. IG password)."""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.settings import settings

# Derive a 32-byte Fernet key from credential_encryption_key when an operator
# has set one, otherwise fall back to secret_key (the pre-existing behavior).
# Do not reuse secret_key here as anything more than a fallback: it also
# signs auth JWTs and reset/verification tokens, so a single leak of it used
# to mean both full account takeover *and* decryption of every stored IG
# password. Set CREDENTIAL_ENCRYPTION_KEY to split the two — see
# scripts/rotate_credential_encryption_key.py to migrate existing rows.
_key_source = settings.credential_encryption_key or settings.secret_key
_key = base64.urlsafe_b64encode(hashlib.sha256(_key_source.encode()).digest())
_fernet = Fernet(_key)


def encrypt(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode()).decode()
