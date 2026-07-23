from pathlib import Path

from app.config import settings
from app.utils.supabase import get_supabase

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
            return self._upload_supabase(bucket, path, data, content_type)
        return self._upload_local(bucket, path, data)

    def _upload_local(self, bucket: str, path: str, data: bytes) -> str:
        full_path = UPLOAD_DIR / bucket / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        return str(full_path)

    def _upload_supabase(
        self, bucket: str, path: str, data: bytes, content_type: str
    ) -> str:
        client = get_supabase()
        if not client:
            return self._upload_local(bucket, path, data)
        client.storage.from_(bucket).upload(
            path=path,
            file=data,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        return client.storage.from_(bucket).get_public_url(path)

    async def delete(self, bucket: str, path: str) -> None:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            client = get_supabase()
            if client:
                client.storage.from_(bucket).remove([path])
                return
        full_path = Path(path)
        if full_path.exists():
            full_path.unlink()

    async def get_download_url(self, bucket: str, path: str) -> str:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            client = get_supabase()
            if client:
                return client.storage.from_(bucket).get_public_url(path)
        return f"/uploads/{path}"

    async def exists(self, bucket: str, path: str) -> bool:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            client = get_supabase()
            if client:
                try:
                    client.storage.from_(bucket).get_public_url(path)
                    files = client.storage.from_(bucket).list(path.rsplit("/", 1)[0] or "")
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
                return client.storage.from_(bucket).download(path)
        full_path = UPLOAD_DIR / bucket / path
        return full_path.read_bytes()
