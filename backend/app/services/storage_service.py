import asyncio
from pathlib import Path

from app.config import settings
from app.utils.supabase import get_supabase

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class StorageService:
    """Local file storage with optional Supabase fallback.

    All methods accept a bucket and a relative path (e.g. ``user_id/project/file.pdf``).
    ``upload()`` always returns the relative path. ``get_download_url()``
    returns an HTTP-accessible URL regardless of backend.
    """

    async def upload(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            client = get_supabase()
            if client:
                await asyncio.to_thread(
                    self._upload_supabase, client, bucket, path, data, content_type,
                )
                return path
        self._upload_local(bucket, path, data)
        return path

    def _upload_local(self, bucket: str, path: str, data: bytes) -> None:
        full_path = UPLOAD_DIR / bucket / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)

    def _upload_supabase(
        self, client, bucket: str, path: str, data: bytes, content_type: str,
    ) -> None:
        client.storage.from_(bucket).upload(
            path=path,
            file=data,
            file_options={"content-type": content_type, "upsert": "true"},
        )

    async def delete(self, bucket: str, path: str) -> None:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            client = get_supabase()
            if client:
                await asyncio.to_thread(client.storage.from_(bucket).remove, [path])
                return
        full_path = UPLOAD_DIR / bucket / path
        if full_path.exists():
            full_path.unlink()

    async def get_download_url(self, bucket: str, path: str) -> str:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            client = get_supabase()
            if client:
                return await asyncio.to_thread(
                    client.storage.from_(bucket).get_public_url, path,
                )
        return f"/uploads/{bucket}/{path}"

    async def exists(self, bucket: str, path: str) -> bool:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            client = get_supabase()
            if client:
                try:
                    files = await asyncio.to_thread(
                        client.storage.from_(bucket).list, (path.rsplit("/", 1)[0] or ""),
                    )
                    filename = path.rsplit("/", 1)[-1]
                    return any(f.get("name") == filename for f in files)
                except Exception:
                    return False
        full_path = UPLOAD_DIR / bucket / path
        return full_path.exists()

    async def download_bytes(self, bucket: str, path: str) -> bytes:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            client = get_supabase()
            if client:
                return await asyncio.to_thread(client.storage.from_(bucket).download, path)
        full_path = UPLOAD_DIR / bucket / path
        return full_path.read_bytes()
