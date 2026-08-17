import os

from cryptography.fernet import Fernet, InvalidToken


def _get_fernet():
    key = os.getenv("VISIONX_CREDENTIAL_ENCRYPTION_KEY")

    if not key:
        raise RuntimeError(
            "VISIONX_CREDENTIAL_ENCRYPTION_KEY is not configured."
        )

    try:
        return Fernet(key.encode("utf-8"))
    except Exception as exc:
        raise RuntimeError(
            "VISIONX_CREDENTIAL_ENCRYPTION_KEY is invalid."
        ) from exc


def encrypt_credential(value):
    if value is None:
        return ""

    value = str(value)

    if not value:
        return ""

    return _get_fernet().encrypt(
        value.encode("utf-8")
    ).decode("utf-8")


def decrypt_credential(value):
    if value is None:
        return ""

    value = str(value)

    if not value:
        return ""

    try:
        return _get_fernet().decrypt(
            value.encode("utf-8")
        ).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError(
            "Credential could not be decrypted. "
            "The encryption key may have changed or the value is invalid."
        ) from exc
