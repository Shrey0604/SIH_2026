from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import Engine, create_engine, delete, func, inspect, or_, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    Alert,
    Base,
    Document,
    DocumentChunk,
    DocumentPage,
    Event,
    EventEvidence,
    Formation,
    IngestionJob,
    Well,
    WellFormationInterval,
)
from app.repositories.base import Repository


SEED_TIMESTAMP = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _slug(value: str) -> str:
    return value.lower().replace("_", "-").replace(".", "-")


class SqlAlchemyRepository(Repository):
    def __init__(self, database_url: str, *, connect_args: dict[str, Any] | None = None):
        self.engine: Engine = create_engine(
            database_url,
            connect_args=connect_args or {},
            pool_pre_ping=True,
        )
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)
        if self.engine.dialect.name == "sqlite":
            columns = {
                column["name"]
                for column in inspect(self.engine).get_columns("document_chunks")
            }
            additions = {
                "embedding_provider": "VARCHAR(32)",
                "embedding_model": "VARCHAR(96)",
                "embedding_dimension": "INTEGER",
            }
            with self.engine.begin() as connection:
                for name, sql_type in additions.items():
                    if name not in columns:
                        connection.execute(
                            text(
                                f"ALTER TABLE document_chunks ADD COLUMN {name} {sql_type}"
                            )
                        )

    def seed_from_file(self, fixture_path: Path) -> None:
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        formations = {
            name: Formation(id=f"formation-{_slug(name)}", name=name, code=name.upper())
            for name in fixture["formations"]
        }
        wells = {
            item["name"]: Well(
                id=item["id"],
                name=item["name"],
                is_active=item["is_active"],
                latitude=item["lat"],
                longitude=item["lon"],
                field_name=item["field_name"],
                max_md_m=item["max_md_m"],
                status=item["status"],
                source_kind="SYNTHETIC",
                well_scope=item.get("well_scope", "LOCAL_OFFSET"),
            )
            for item in fixture["wells"]
        }

        document_names = sorted({event["document"] for event in fixture["events"]})
        event_well_by_document = {
            event["document"]: wells[event["well"]].id for event in fixture["events"]
        }
        documents = {
            filename: Document(
                id=f"document-{_slug(filename)}",
                well_id=event_well_by_document[filename],
                title=filename.removesuffix(".pdf").replace("_", " "),
                document_type="WCR" if "WCR" in filename else "DDR",
                filename=filename,
                storage_path=f"demo_data/{filename}",
                page_count=max(
                    event["page"]
                    for event in fixture["events"]
                    if event["document"] == filename
                ),
                sha256=hashlib.sha256(f"nwis:{filename}".encode()).hexdigest(),
                ingestion_status="COMPLETED",
                source_kind="SYNTHETIC",
                created_at=SEED_TIMESTAMP,
            )
            for filename in document_names
        }

        with self.session_factory.begin() as session:
            for formation in formations.values():
                session.merge(formation)
            for well in wells.values():
                session.merge(well)

            for well_name, intervals in fixture["formation_intervals"].items():
                for formation_name, (top_md_m, base_md_m) in intervals.items():
                    session.merge(
                        WellFormationInterval(
                            id=f"interval-{wells[well_name].id}-{_slug(formation_name)}",
                            well_id=wells[well_name].id,
                            formation_id=formations[formation_name].id,
                            top_md_m=top_md_m,
                            base_md_m=base_md_m,
                            top_tvd_m=None,
                            base_tvd_m=None,
                        )
                    )

            for document in documents.values():
                session.merge(document)

            for item in fixture["events"]:
                event = Event(
                    id=item["id"],
                    well_id=wells[item["well"]].id,
                    formation_id=formations[item["formation"]].id,
                    hazard_type=item["hazard_type"],
                    start_md_m=item["start_md_m"],
                    end_md_m=item.get("end_md_m"),
                    severity=item["severity"],
                    description=item["description"],
                    historical_response=item.get("historical_response"),
                    extraction_confidence=item["extraction_confidence"],
                    source="SEEDED",
                    created_at=SEED_TIMESTAMP,
                )
                session.merge(event)
                evidence_text = item["description"]
                if item.get("historical_response"):
                    evidence_text += (
                        f" Historical response observed: {item['historical_response']}"
                    )
                session.merge(
                    EventEvidence(
                        id=f"evidence-{item['id']}",
                        event_id=item["id"],
                        document_id=documents[item["document"]].id,
                        page_number=item["page"],
                        evidence_text=evidence_text,
                        bbox_json=None,
                    )
                )

    def reset_runtime_data(self) -> None:
        with self.session_factory.begin() as session:
            session.execute(delete(Alert))

    def health_check(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def counts(self) -> dict[str, int]:
        tables = {
            "wells": Well,
            "formations": Formation,
            "documents": Document,
            "events": Event,
            "evidence": EventEvidence,
            "document_pages": DocumentPage,
            "document_chunks": DocumentChunk,
            "ingestion_jobs": IngestionJob,
            "alerts": Alert,
        }
        with self.session_factory() as session:
            return {
                name: session.scalar(select(func.count()).select_from(model)) or 0
                for name, model in tables.items()
            }

    def seed_snapshot(self) -> dict[str, Any]:
        with self.session_factory() as session:
            wells = session.execute(
                select(Well.id, Well.name, Well.is_active).order_by(Well.id)
            ).all()
            events = session.execute(
                select(
                    Event.id,
                    Event.well_id,
                    Event.formation_id,
                    Event.hazard_type,
                    Event.start_md_m,
                    Event.end_md_m,
                ).order_by(Event.id)
            ).all()
            evidence = session.execute(
                select(
                    EventEvidence.id,
                    EventEvidence.event_id,
                    EventEvidence.document_id,
                    EventEvidence.page_number,
                ).order_by(EventEvidence.id)
            ).all()
        return {
            "wells": [tuple(row) for row in wells],
            "events": [tuple(row) for row in events],
            "evidence": [tuple(row) for row in evidence],
        }

    def list_wells(self) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            rows = session.scalars(select(Well).order_by(Well.name)).all()
            return [
                {
                    "id": row.id,
                    "name": row.name,
                    "is_active": row.is_active,
                    "latitude": row.latitude,
                    "longitude": row.longitude,
                    "field_name": row.field_name,
                    "max_md_m": row.max_md_m,
                    "status": row.status,
                    "source_kind": row.source_kind,
                    "well_scope": row.well_scope,
                }
                for row in rows
            ]

    def list_formation_intervals(self) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            rows = session.execute(
                select(WellFormationInterval, Formation)
                .join(Formation, Formation.id == WellFormationInterval.formation_id)
                .order_by(WellFormationInterval.well_id, WellFormationInterval.top_md_m)
            ).all()
            return [
                {
                    "id": interval.id,
                    "well_id": interval.well_id,
                    "formation_id": interval.formation_id,
                    "formation_name": formation.name,
                    "formation_code": formation.code,
                    "top_md_m": interval.top_md_m,
                    "base_md_m": interval.base_md_m,
                    "top_tvd_m": interval.top_tvd_m,
                    "base_tvd_m": interval.base_tvd_m,
                }
                for interval, formation in rows
            ]

    def list_events(self) -> list[dict[str, Any]]:
        evidence_exists = (
            select(func.count(EventEvidence.id))
            .where(EventEvidence.event_id == Event.id)
            .correlate(Event)
            .scalar_subquery()
        )
        with self.session_factory() as session:
            rows = session.execute(
                select(Event, Formation.name, evidence_exists.label("evidence_count"))
                .outerjoin(Formation, Formation.id == Event.formation_id)
                .order_by(Event.id)
            ).all()
            return [
                {
                    "id": event.id,
                    "well_id": event.well_id,
                    "formation_id": event.formation_id,
                    "formation_name": formation_name,
                    "hazard_type": event.hazard_type,
                    "start_md_m": event.start_md_m,
                    "end_md_m": event.end_md_m,
                    "severity": event.severity,
                    "description": event.description,
                    "historical_response": event.historical_response,
                    "extraction_confidence": event.extraction_confidence,
                    "source": event.source,
                    "has_exact_page_evidence": evidence_count > 0,
                }
                for event, formation_name, evidence_count in rows
            ]

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        with self.session_factory() as session:
            row = session.execute(
                select(Event, Formation.name, Well.name)
                .outerjoin(Formation, Formation.id == Event.formation_id)
                .join(Well, Well.id == Event.well_id)
                .where(Event.id == event_id)
            ).one_or_none()
        if row is None:
            return None
        event, formation_name, well_name = row
        evidence = self.list_event_evidence(event_id)
        return {
            "id": event.id,
            "well_id": event.well_id,
            "well_name": well_name,
            "formation_id": event.formation_id,
            "formation_name": formation_name,
            "hazard_type": event.hazard_type,
            "start_md_m": event.start_md_m,
            "end_md_m": event.end_md_m,
            "severity": event.severity,
            "description": event.description,
            "historical_response": event.historical_response,
            "extraction_confidence": event.extraction_confidence,
            "source": event.source,
            "has_exact_page_evidence": bool(evidence),
            "evidence": evidence,
        }

    def list_event_evidence(self, event_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            rows = session.execute(
                select(EventEvidence, Document)
                .join(Document, Document.id == EventEvidence.document_id)
                .where(EventEvidence.event_id == event_id)
                .order_by(EventEvidence.page_number, EventEvidence.id)
            ).all()
            return [
                {
                    "id": evidence.id,
                    "event_id": evidence.event_id,
                    "document_id": evidence.document_id,
                    "document_title": document.title,
                    "filename": document.filename,
                    "page_number": evidence.page_number,
                    "evidence_text": evidence.evidence_text,
                    "bbox_json": json.loads(evidence.bbox_json)
                    if evidence.bbox_json
                    else None,
                    "source_kind": document.source_kind,
                }
                for evidence, document in rows
            ]

    @staticmethod
    def _document_payload(document: Document) -> dict[str, Any]:
        return {
            "id": document.id,
            "well_id": document.well_id,
            "title": document.title,
            "document_type": document.document_type,
            "filename": document.filename,
            "storage_path": document.storage_path,
            "page_count": document.page_count,
            "sha256": document.sha256,
            "ingestion_status": document.ingestion_status,
            "source_kind": document.source_kind,
            "created_at": document.created_at.isoformat(),
        }

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        with self.session_factory() as session:
            document = session.get(Document, document_id)
            return self._document_payload(document) if document else None

    def list_documents(self) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            documents = session.scalars(
                select(Document).order_by(Document.created_at.desc(), Document.title)
            ).all()
            return [self._document_payload(document) for document in documents]

    def find_document_by_sha256(self, sha256: str) -> dict[str, Any] | None:
        with self.session_factory() as session:
            row = session.execute(
                select(Document, IngestionJob.id)
                .outerjoin(IngestionJob, IngestionJob.document_id == Document.id)
                .where(Document.sha256 == sha256)
            ).one_or_none()
            if row is None:
                return None
            document, job_id = row
            return self._document_payload(document) | {"ingestion_job_id": job_id}

    def create_ingestion(
        self, document: dict[str, Any], job: dict[str, Any]
    ) -> None:
        with self.session_factory.begin() as session:
            session.add(Document(**document))
            job_values = dict(job)
            stages = job_values.pop("stages")
            session.add(
                IngestionJob(
                    **{
                        **job_values,
                        "stages_json": json.dumps(stages, sort_keys=True),
                    }
                )
            )

    def update_ingestion_job(
        self,
        job_id: str,
        *,
        status: str,
        stages: dict[str, str],
        error_message: str | None = None,
        cached_verified_extraction: bool = False,
    ) -> None:
        now = datetime.now(timezone.utc)
        with self.session_factory.begin() as session:
            job = session.get(IngestionJob, job_id)
            if job is None:
                raise KeyError(f"Ingestion job {job_id} was not found")
            job.status = status
            job.stages_json = json.dumps(stages, sort_keys=True)
            job.error_message = error_message
            job.cached_verified_extraction = cached_verified_extraction
            job.updated_at = now
            document = session.get(Document, job.document_id)
            if document is not None:
                document.ingestion_status = status.upper()

    def get_ingestion_job(self, job_id: str) -> dict[str, Any] | None:
        with self.session_factory() as session:
            row = session.execute(
                select(IngestionJob, Document)
                .join(Document, Document.id == IngestionJob.document_id)
                .where(IngestionJob.id == job_id)
            ).one_or_none()
            if row is None:
                return None
            job, document = row
            chunk_count = session.scalar(
                select(func.count(DocumentChunk.id)).where(
                    DocumentChunk.document_id == document.id
                )
            ) or 0
            event_ids = session.scalars(
                select(EventEvidence.event_id)
                .where(EventEvidence.document_id == document.id)
                .order_by(EventEvidence.event_id)
            ).all()
        return {
            "id": job.id,
            "document_id": job.document_id,
            "filename": document.filename,
            "status": job.status,
            "stages": json.loads(job.stages_json),
            "error_message": job.error_message,
            "cached_verified_extraction": job.cached_verified_extraction,
            "page_count": document.page_count,
            "chunk_count": chunk_count,
            "events": [
                event
                for event_id in event_ids
                if (event := self.get_event(event_id)) is not None
            ],
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
        }

    def save_document_pages(
        self, document_id: str, pages: list[dict[str, Any]]
    ) -> None:
        with self.session_factory.begin() as session:
            document = session.get(Document, document_id)
            if document is None:
                raise KeyError(f"Document {document_id} was not found")
            for page in pages:
                session.merge(DocumentPage(**page))
            document.page_count = len(pages)

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
        now = datetime.now(timezone.utc)
        with self.session_factory.begin() as session:
            document = session.get(Document, document_id)
            job = session.get(IngestionJob, job_id)
            if document is None or job is None:
                raise KeyError("Ingestion document or job was not found")
            for page in pages:
                session.merge(DocumentPage(**page))
            for chunk in chunks:
                session.add(
                    DocumentChunk(
                        **{
                            **chunk,
                            "embedding": json.dumps(chunk["embedding"]),
                        }
                    )
                )
            for item in events:
                event_values = dict(item)
                evidence_text = event_values.pop("evidence_text")
                page_number = event_values.pop("page_number")
                session.add(Event(**event_values))
                session.add(
                    EventEvidence(
                        id=f"evidence-{event_values['id']}",
                        event_id=event_values["id"],
                        document_id=document_id,
                        page_number=page_number,
                        evidence_text=evidence_text,
                        bbox_json=None,
                    )
                )
            document.page_count = len(pages)
            document.ingestion_status = "COMPLETED"
            job.status = "completed"
            job.stages_json = json.dumps(stages, sort_keys=True)
            job.error_message = None
            job.cached_verified_extraction = cached_verified_extraction
            job.updated_at = now

    def list_document_chunks(self, document_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            chunks = session.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.page_number, DocumentChunk.chunk_index)
            ).all()
            return [
                {
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "embedding": (
                        json.loads(chunk.embedding)
                        if isinstance(chunk.embedding, str)
                        else chunk.embedding
                    ),
                    "embedding_provider": chunk.embedding_provider,
                    "embedding_model": chunk.embedding_model,
                    "embedding_dimension": chunk.embedding_dimension,
                }
                for chunk in chunks
            ]

    def invalidate_incompatible_embeddings(
        self, *, provider: str, model: str, dimension: int
    ) -> int:
        with self.session_factory.begin() as session:
            chunks = session.scalars(
                select(DocumentChunk).where(
                    DocumentChunk.embedding.is_not(None),
                    or_(
                        DocumentChunk.embedding_provider.is_(None),
                        DocumentChunk.embedding_provider != provider,
                        DocumentChunk.embedding_model.is_(None),
                        DocumentChunk.embedding_model != model,
                        DocumentChunk.embedding_dimension.is_(None),
                        DocumentChunk.embedding_dimension != dimension,
                    ),
                )
            ).all()
            for chunk in chunks:
                chunk.embedding = None
                chunk.embedding_provider = None
                chunk.embedding_model = None
                chunk.embedding_dimension = None
            return len(chunks)

    def update_chunk_embeddings(
        self,
        updates: list[dict[str, Any]],
        *,
        provider: str,
        model: str,
        dimension: int,
    ) -> None:
        with self.session_factory.begin() as session:
            for update in updates:
                chunk = session.get(DocumentChunk, update["id"])
                if chunk is None:
                    raise KeyError(f"Document chunk {update['id']} was not found")
                vector = update["embedding"]
                if len(vector) != dimension:
                    raise ValueError(
                        f"Embedding for {chunk.id} did not have dimension {dimension}"
                    )
                chunk.embedding = json.dumps(vector)
                chunk.embedding_provider = provider
                chunk.embedding_model = model
                chunk.embedding_dimension = dimension

    def search_chunks(
        self,
        query_embedding: list[float],
        *,
        provider: str,
        model: str,
        dimension: int,
        top_k: int = 6,
    ) -> list[dict[str, Any]]:
        if len(query_embedding) != dimension:
            raise ValueError("Query embedding dimension does not match the active index")
        query = np.asarray(query_embedding, dtype=float)
        query_norm = float(np.linalg.norm(query))
        if query_norm == 0:
            return []
        scored = []
        for document in self.list_documents():
            for chunk in self.list_document_chunks(document["id"]):
                if chunk["embedding"] is None:
                    continue
                if (
                    chunk["embedding_provider"] != provider
                    or chunk["embedding_model"] != model
                    or chunk["embedding_dimension"] != dimension
                ):
                    continue
                embedding_value = chunk["embedding"]
                if isinstance(embedding_value, str):
                    embedding_value = json.loads(embedding_value)
                embedding = np.asarray(embedding_value, dtype=float)
                if embedding.shape != query.shape:
                    continue
                denominator = query_norm * float(np.linalg.norm(embedding))
                similarity = float(np.dot(query, embedding) / denominator) if denominator else 0.0
                scored.append(
                    chunk
                    | {
                        "similarity": round(similarity, 6),
                        "document_title": document["title"],
                        "filename": document["filename"],
                    }
                )
        return sorted(scored, key=lambda item: item["similarity"], reverse=True)[:top_k]
