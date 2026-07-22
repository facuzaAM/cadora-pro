import io
import os
from pathlib import Path

from app.config import settings

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class StorageService:
    """Local file storage with optional Supabase fallback."""

    async def upload(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            return await self._upload_supabase(bucket, path, data, content_type)
        return await self._upload_local(bucket, path, data)

    async def _upload_local(self, bucket: str, path: str, data: bytes) -> str:
        full_path = UPLOAD_DIR / bucket / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        return str(full_path)

    async def _upload_supabase(
        self, bucket: str, path: str, data: bytes, content_type: str
    ) -> str:
        from supabase import create_client

        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        client.storage.from_(bucket).upload(
            path=path,
            file=data,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        public_url = client.storage.from_(bucket).get_public_url(path)
        return public_url

    async def delete(self, bucket: str, path: str) -> None:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            from supabase import create_client

            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            client.storage.from_(bucket).remove([path])
        else:
            full_path = Path(path)
            if full_path.exists():
                full_path.unlink()

    async def get_download_url(self, bucket: str, path: str) -> str:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            from supabase import create_client

            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            return client.storage.from_(bucket).get_public_url(path)
        return f"/uploads/{path}"
