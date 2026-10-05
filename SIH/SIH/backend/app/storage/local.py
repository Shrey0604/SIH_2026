from __future__ import annotations

from pathlib import Path

from app.storage.base import StorageAdapter


class LocalStorageAdapter(StorageAdapter):
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, object_path: str) -> Path:
        target = (self.root / object_path.lstrip("/")).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError("Storage path escapes the configured local root")
        return target

    def put(self, object_path: str, content: bytes, content_type: str) -> str:
        del content_type
        target = self._safe_path(object_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return object_path.lstrip("/")

    def get(self, object_path: str) -> bytes:
        return self._safe_path(object_path).read_bytes()

