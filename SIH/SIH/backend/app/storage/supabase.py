from __future__ import annotations

from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.storage.base import StorageAdapter


class SupabaseStorageAdapter(StorageAdapter):
    """Small server-side adapter over Supabase Storage's object API."""

    def __init__(self, url: str, service_role_key: str, bucket: str):
        self.url = url.rstrip("/")
        self.service_role_key = service_role_key
        self.bucket = bucket

    def _object_url(self, object_path: str) -> str:
        safe_bucket = quote(self.bucket, safe="")
        safe_path = quote(object_path.lstrip("/"), safe="/")
        return f"{self.url}/storage/v1/object/{safe_bucket}/{safe_path}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }

    def put(self, object_path: str, content: bytes, content_type: str) -> str:
        headers = self._headers() | {
            "Content-Type": content_type,
            "x-upsert": "true",
        }
        request = Request(
            self._object_url(object_path), data=content, headers=headers, method="POST"
        )
        try:
            with urlopen(request, timeout=20) as response:
                if response.status not in {200, 201}:
                    raise RuntimeError(f"Supabase storage returned {response.status}")
        except HTTPError as error:
            raise RuntimeError(
                f"Supabase storage upload failed ({error.code})"
            ) from error
        return object_path.lstrip("/")

    def get(self, object_path: str) -> bytes:
        request = Request(self._object_url(object_path), headers=self._headers())
        try:
            with urlopen(request, timeout=20) as response:
                return response.read()
        except HTTPError as error:
            raise RuntimeError(
                f"Supabase storage download failed ({error.code})"
            ) from error

