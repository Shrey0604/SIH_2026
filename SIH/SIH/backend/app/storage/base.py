from __future__ import annotations

from abc import ABC, abstractmethod


class StorageAdapter(ABC):
    @abstractmethod
    def put(self, object_path: str, content: bytes, content_type: str) -> str:
        """Store bytes and return a stable object path."""

    @abstractmethod
    def get(self, object_path: str) -> bytes:
        """Read stored bytes."""

