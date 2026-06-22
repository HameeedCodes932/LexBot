import logging
from typing import Optional
from supabase import create_client, Client

import config

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self._client: Optional[Client] = None

    @property
    def client(self) -> Optional[Client]:
        if self._client is None and config.SUPABASE_URL and config.SUPABASE_KEY:
            try:
                self._client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
            except Exception as exc:
                logger.warning("Supabase client init failed: %s", exc)
        return self._client

    def is_available(self) -> bool:
        return self.client is not None

    def upload_file(self, file_data: bytes, file_path: str, content_type: str = "application/octet-stream") -> Optional[str]:
        if not self.is_available():
            logger.warning("Supabase not configured — file not stored remotely")
            return None
        try:
            self.client.storage.from_(config.SUPABASE_STORAGE_BUCKET).upload(
                file_path, file_data, {"content-type": content_type}
            )
            public_url = self.client.storage.from_(config.SUPABASE_STORAGE_BUCKET).get_public_url(file_path)
            logger.info("Uploaded %s to Supabase Storage", file_path)
            return public_url
        except Exception as exc:
            logger.warning("Supabase upload failed for %s: %s", file_path, exc)
            return None

    def download_file(self, file_path: str) -> Optional[bytes]:
        if not self.is_available():
            return None
        try:
            return self.client.storage.from_(config.SUPABASE_STORAGE_BUCKET).download(file_path)
        except Exception as exc:
            logger.warning("Supabase download failed for %s: %s", file_path, exc)
            return None

    def delete_file(self, file_path: str) -> bool:
        if not self.is_available():
            return False
        try:
            self.client.storage.from_(config.SUPABASE_STORAGE_BUCKET).remove([file_path])
            return True
        except Exception as exc:
            logger.warning("Supabase delete failed for %s: %s", file_path, exc)
            return False

    def list_files(self, prefix: str = "") -> list:
        if not self.is_available():
            return []
        try:
            return self.client.storage.from_(config.SUPABASE_STORAGE_BUCKET).list(prefix)
        except Exception as exc:
            logger.warning("Supabase list failed: %s", exc)
            return []


storage_service = StorageService()
