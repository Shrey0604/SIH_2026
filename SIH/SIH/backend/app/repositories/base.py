from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class Repository(ABC):
    """Persistence boundary shared by local SQLite and hosted PostgreSQL."""

    @abstractmethod
    def initialize(self) -> None:
        """Create application schema when it does not already exist."""

    @abstractmethod
    def seed_from_file(self, fixture_path: Path) -> None:
        """Idempotently load deterministic domain seed data."""

    @abstractmethod
    def reset_runtime_data(self) -> None:
        """Clear transient state without modifying institutional-memory seed data."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return whether the persistence connection is usable."""

    @abstractmethod
    def counts(self) -> dict[str, int]:
        """Return compact counts used by health checks and deterministic tests."""

    @abstractmethod
    def seed_snapshot(self) -> dict[str, Any]:
        """Return stable seed fields for reproducibility verification."""

    @abstractmethod
    def list_wells(self) -> list[dict[str, Any]]:
        """Return wells as repository-neutral records."""

    @abstractmethod
    def list_formation_intervals(self) -> list[dict[str, Any]]:
        """Return formation intervals with formation names."""

    @abstractmethod
    def list_events(self) -> list[dict[str, Any]]:
        """Return historical events with evidence availability."""

    @abstractmethod
    def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Return one historical event with its exact evidence references."""

    @abstractmethod
    def list_event_evidence(self, event_id: str) -> list[dict[str, Any]]:
        """Return stored document/page evidence for an event."""

    @abstractmethod
    def get_document(self, document_id: str) -> dict[str, Any] | None:
        """Return one document record."""

    @abstractmethod
    def list_documents(self) -> list[dict[str, Any]]:
        """Return stored document records."""

    @abstractmethod
    def find_document_by_sha256(self, sha256: str) -> dict[str, Any] | None:
        """Return an existing document with the same content hash."""

    @abstractmethod
    def create_ingestion(
        self, document: dict[str, Any], job: dict[str, Any]
    ) -> None:
        """Create an uploaded document and its ingestion job."""

    @abstractmethod
    def update_ingestion_job(
        self,
        job_id: str,
        *,
        status: str,
        stages: dict[str, str],
        error_message: str | None = None,
        cached_verified_extraction: bool = False,
    ) -> None:
        """Update observable ingestion progress."""

    @abstractmethod
    def get_ingestion_job(self, job_id: str) -> dict[str, Any] | None:
        """Return ingestion state and result counts."""

    @abstractmethod
    def save_document_pages(
        self, document_id: str, pages: list[dict[str, Any]]
    ) -> None:
        """Persist extracted page text even when later AI stages cannot complete."""

    @abstractmethod
    def persist_ingestion_result(
        self,
        *,
        document_id: str,
        job_id: str,
        pages: list[dict[str, Any]],
        chunks: list[dict[str, Any]],
        events: list[dict[str, Any]],
        stages: dict[str, str],
        cached_verified_extraction: bool,
    ) -> None:
        """Atomically make validated pages, chunks, events, and evidence visible."""

    @abstractmethod
    def list_document_chunks(self, document_id: str) -> list[dict[str, Any]]:
        """Return page-aware indexed chunks for a document."""

    @abstractmethod
    def invalidate_incompatible_embeddings(
        self, *, provider: str, model: str, dimension: int
    ) -> int:
        """Clear vectors whose provider/model/dimension does not match the active space."""

    @abstractmethod
    def update_chunk_embeddings(
        self,
        updates: list[dict[str, Any]],
        *,
        provider: str,
        model: str,
        dimension: int,
    ) -> None:
        """Persist rebuilt vectors with compatibility metadata."""

    @abstractmethod
    def search_chunks(
        self,
        query_embedding: list[float],
        *,
        provider: str,
        model: str,
        dimension: int,
        top_k: int = 6,
    ) -> list[dict[str, Any]]:
        """Return the nearest embedded chunks using the configured fallback path."""
