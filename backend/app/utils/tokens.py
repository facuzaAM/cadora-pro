import hashlib


def hash_secret(value: str) -> str:
    """SHA-256 hex digest for storing opaque secrets at rest.

    Used for refresh tokens and short numeric codes so a database leak
    does not expose the raw credentials.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
