from __future__ import annotations

from typing import Any

import pymupdf

from app.config import ROOT_DIR
from app.repositories.base import Repository
from app.storage.base import StorageAdapter


class EvidenceService:
    def __init__(self, repository: Repository, storage: StorageAdapter):
        self.repository = repository
        self.storage = storage

    def event_with_evidence(self, event_id: str) -> dict[str, Any] | None:
        return self.repository.get_event(event_id)

    def _document_bytes(self, document: dict[str, Any]) -> bytes:
        storage_path = str(document["storage_path"])
        if storage_path.startswith("demo_data/"):
            path = (ROOT_DIR / storage_path).resolve()
            demo_root = (ROOT_DIR / "demo_data").resolve()
            if not path.is_relative_to(demo_root):
                raise ValueError("Demo document path escapes demo_data")
            return path.read_bytes()
        return self.storage.get(storage_path)

    def render_page_png(
        self, document_id: str, page_number: int, *, scale: float = 1.7
    ) -> tuple[bytes, dict[str, Any]]:
        document = self.repository.get_document(document_id)
        if document is None:
            raise FileNotFoundError("Document not found")
        if page_number < 1 or page_number > document["page_count"]:
            raise IndexError("Page is outside the document")
        pdf_bytes = self._document_bytes(document)
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
            page = pdf.load_page(page_number - 1)
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            return pixmap.tobytes("png"), document

    def document_pdf(self, document_id: str) -> tuple[bytes, dict[str, Any]]:
        document = self.repository.get_document(document_id)
        if document is None:
            raise FileNotFoundError("Document not found")
        return self._document_bytes(document), document
