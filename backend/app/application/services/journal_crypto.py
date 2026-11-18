"""Encryption for the journal lock. The key is derived from the user's PIN with scrypt every time
it is needed and is never stored; losing the PIN means losing the locked entries."""
import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

CHECK_VALUE = b"daycompass-journal-lock"
MIN_PIN = 4
MAX_PIN = 64


def new_salt() -> bytes:
    return os.urandom(16)


def make_cipher(pin: str, salt: bytes) -> Fernet:
    key = hashlib.scrypt(pin.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return Fernet(base64.urlsafe_b64encode(key))


def make_check(cipher: Fernet) -> bytes:
    return cipher.encrypt(CHECK_VALUE)


def is_correct(cipher: Fernet, check_token: bytes) -> bool:
    try:
        return cipher.decrypt(check_token) == CHECK_VALUE
    except InvalidToken:
        return False
