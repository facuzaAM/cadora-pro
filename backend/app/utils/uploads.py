"""Shared upload helpers: validation, size limits and safe temp files."""

import os
import tempfile
import uuid as _uuid
from collections.abc import Collection

from fastapi import HTTPException, UploadFile
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_413_CONTENT_TOO_LARGE

MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "pdf": (b"%PDF-",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "tiff": (b"II*\x00", b"MM\x00*"),
}


def get_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_extension(
    file: UploadFile,
    allowed: Collection[str],
    *,
    detail: str | None = None,
) -> str:
    """Validate that the filename has an allowed extension and return it.

    Raises HTTPException(400) when the filename is missing or unsupported.
    """
    if not file.filename:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Archivo no proporcionado")
    ext = get_extension(file.filename)
    if f".{ext}" not in allowed:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=detail or f"Formato .{ext} no soportado",
        )
    return ext


def validate_magic_bytes(file_type: str, content: bytes) -> None:
    """Reject files whose magic bytes do not match their declared extension."""
    signatures = MAGIC_SIGNATURES.get(file_type)
    if signatures is not None and not any(
        content.startswith(sig) for sig in signatures
    ):
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"El archivo no parece ser un {file_type.upper()} válido",
        )


async def read_upload_with_limit(file: UploadFile, max_bytes: int, detail: str) -> bytes:
    """Read an upload in chunks, rejecting content larger than ``max_bytes``."""
    content = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > max_bytes:
            raise HTTPException(status_code=HTTP_413_CONTENT_TOO_LARGE, detail=detail)
    return bytes(content)


def make_temp_path(prefix: str, filename: str | None = None) -> str:
    """Create a unique, safely named temp file path."""
    safe_name = os.path.basename(filename or "upload").replace("/", "").replace("\\", "")
    tag = _uuid.uuid4().hex[:8]
    fd, path = tempfile.mkstemp(suffix=f"_{safe_name}", prefix=f"{prefix}_{tag}_")
    os.close(fd)
    return path
