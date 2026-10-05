from __future__ import annotations

import hashlib
import math
import re
import uuid
from datetime import datetime, timezone
from pathlib import PurePath

from app.ai import (
    AIProvider,
    ExtractedEvent,
    ExtractionResult,
    ProviderResponseError,
    ProviderUnavailableError,
)
from app.config import Settings
from app.repositories.base import Repository
from app.services.pdf_service import (
    chunk_page_text,
    extract_native_pages,
    normalized_evidence,
    render_page_for_vision,
    validate_pdf,
)
from app.services.embedding_service import EmbeddingService
from app.storage.base import StorageAdapter


MAX_PDF_BYTES = 20 * 1024 * 1024
DEMO_REPORT_SHA256 = "2fb9dc2342558d647e594e49a337f479c580102013b86e6d6da8d726f99ad634"
STAGE_NAMES = ("READ", "OCR", "EXTRACT", "VERIFY", "INDEX")
STAGE_STATUS = {
    "READ": "reading",
    "OCR": "recovering_scan",
    "EXTRACT": "extracting",
    "VERIFY": "validating",
    "INDEX": "indexing",
}


def initial_stages() -> dict[str, str]:
    return {stage: "pending" for stage in STAGE_NAMES}


def _safe_filename(filename: str) -> str:
    name = PurePath(filename).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return cleaned or "report.pdf"


def deterministic_embedding(text: str, dimensions: int = 768) -> list[float]:
    """Local cached-demo fallback; not used as a learned model or accuracy claim."""

    vector = [0.0] * dimensions
    for token in re.findall(r"[a-z0-9]+", text.casefold()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += -1.0 if digest[4] & 1 else 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def cached_demo_extraction() -> ExtractionResult:
    return ExtractionResult(
        events=[
            ExtractedEvent(
                hazard_type="MUD_LOSS",
                formation="Barail",
                start_md_m=3210,
                end_md_m=3218,
                severity="MEDIUM",
                description=(
                    "Partial circulation loss observed while drilling the Barail interval."
                ),
                historical_response=(
                    "Flow was reduced and the interval was monitored before drilling resumed."
                ),
                page_number=2,
                evidence_text=(
                    "At 3210 m MD, partial circulation loss was observed while drilling the "
                    "Barail interval. Returns reduced progressively over the interval from "
                    "3210 m to 3218 m MD."
                ),
                confidence=0.98,
            )
        ]
    )


class IngestionService:
    def __init__(
        self,
        repository: Repository,
        storage: StorageAdapter,
        settings: Settings,
        provider: AIProvider | None,
    ):
        self.repository = repository
        self.storage = storage
        self.settings = settings
        self.provider = provider
        self.embeddings = EmbeddingService(provider, settings)

    def create_upload(
        self,
        *,
        filename: str,
        content_type: str | None,
        content: bytes,
        document_type: str,
        well_id: str = "ctx-rj-01",
    ) -> dict[str, object]:
        safe_filename = _safe_filename(filename)
        if content_type not in {"application/pdf", "application/x-pdf"}:
            raise ValueError("Only PDF uploads are accepted")
        if not safe_filename.lower().endswith(".pdf"):
            raise ValueError("Only files with a .pdf extension are accepted")
        if len(content) > MAX_PDF_BYTES:
            raise ValueError("PDF exceeds the 20 MB upload limit")
        validate_pdf(content)

        sha256 = hashlib.sha256(content).hexdigest()
        existing = self.repository.find_document_by_sha256(sha256)
        if existing and existing.get("ingestion_job_id"):
            existing_job = self.repository.get_ingestion_job(
                str(existing["ingestion_job_id"])
            )
            return {
                "document_id": existing["id"],
                "ingestion_job_id": existing["ingestion_job_id"],
                "status": existing_job["status"] if existing_job else "queued",
                "duplicate": True,
            }

        if not any(well["id"] == well_id for well in self.repository.list_wells()):
            raise ValueError("The selected well does not exist")

        identifier = uuid.uuid4().hex[:16]
        document_id = f"document-upload-{identifier}"
        job_id = f"ingestion-{identifier}"
        object_path = f"uploads/{sha256[:12]}/{safe_filename}"
        stored_path = self.storage.put(object_path, content, "application/pdf")
        now = datetime.now(timezone.utc)
        stages = initial_stages()
        self.repository.create_ingestion(
            {
                "id": document_id,
                "well_id": well_id,
                "title": PurePath(safe_filename).stem.replace("_", " "),
                "document_type": document_type.upper()[:24],
                "filename": safe_filename,
                "storage_path": stored_path,
                "page_count": 0,
                "sha256": sha256,
                "ingestion_status": "QUEUED",
                "source_kind": "UPLOADED",
                "created_at": now,
            },
            {
                "id": job_id,
                "document_id": document_id,
                "status": "queued",
                "stages": stages,
                "error_message": None,
                "cached_verified_extraction": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        return {
            "document_id": document_id,
            "ingestion_job_id": job_id,
            "status": "queued",
            "duplicate": False,
        }

    def _progress(
        self,
        job_id: str,
        stages: dict[str, str],
        stage: str,
        state: str,
        *,
        status: str | None = None,
        error_message: str | None = None,
        cached: bool = False,
    ) -> None:
        stages[stage] = state
        self.repository.update_ingestion_job(
            job_id,
            status=status or STAGE_STATUS[stage],
            stages=stages,
            error_message=error_message,
            cached_verified_extraction=cached,
        )

    def _verify_events(
        self, result: ExtractionResult, pages: list[dict[str, object]]
    ) -> tuple[list[ExtractedEvent], list[str]]:
        page_text = {
            int(page["page_number"]): normalized_evidence(
                str(page["recovered_text"] or page["raw_text"])
            )
            for page in pages
        }
        formations = {
            str(interval["formation_name"]).casefold(): interval["formation_id"]
            for interval in self.repository.list_formation_intervals()
        }
        valid: list[ExtractedEvent] = []
        errors: list[str] = []
        for index, event in enumerate(result.events):
            source = page_text.get(event.page_number)
            if source is None:
                errors.append(f"event {index + 1} cites missing page {event.page_number}")
                continue
            evidence = normalized_evidence(event.evidence_text)
            if not evidence or evidence not in source:
                errors.append(f"event {index + 1} evidence is not present on its cited page")
                continue
            if event.formation is not None and event.formation.casefold() not in formations:
                errors.append(f"event {index + 1} names unknown formation {event.formation}")
                continue
            valid.append(event)
        return valid, errors

    def _extract_verified(
        self,
        pages: list[dict[str, object]],
        *,
        sha256: str,
    ) -> tuple[list[ExtractedEvent], bool]:
        input_pages = [
            {
                "page_number": page["page_number"],
                "text": page["recovered_text"] or page["raw_text"],
            }
            for page in pages
        ]
        last_error = "AI provider unavailable"
        if self.provider is not None:
            feedback: str | None = None
            for _attempt in range(2):
                try:
                    result = self.provider.extract_events(
                        input_pages, validation_feedback=feedback
                    )
                except ProviderResponseError as error:
                    feedback = str(error)
                    last_error = feedback
                    continue
                except ProviderUnavailableError as error:
                    last_error = str(error)
                    break
                valid, errors = self._verify_events(result, pages)
                if not errors:
                    return valid, False
                feedback = "; ".join(errors)
                last_error = feedback

        if self.settings.demo_mode and sha256 == DEMO_REPORT_SHA256:
            cached = cached_demo_extraction()
            valid, errors = self._verify_events(cached, pages)
            if not errors:
                return valid, True
        raise ProviderUnavailableError(last_error)

    def process(self, job_id: str, document_id: str, content: bytes) -> dict[str, object]:
        stages = initial_stages()
        cached = False
        try:
            self._progress(job_id, stages, "READ", "running")
            pages = extract_native_pages(content, document_id)
            self._progress(job_id, stages, "READ", "completed")

            low_text_pages = [page for page in pages if page["text_quality"] < 0.35]
            if low_text_pages:
                self._progress(job_id, stages, "OCR", "running")
                if self.provider is None:
                    raise ProviderUnavailableError(
                        "A low-text page needs vision recovery, but GEMINI_API_KEY is unavailable"
                    )
                for page in low_text_pages:
                    image = render_page_for_vision(content, int(page["page_number"]))
                    recovered = self.provider.recover_scanned_page(
                        image, page_number=int(page["page_number"])
                    )
                    page["recovered_text"] = recovered
                    page["extraction_method"] = "VISION"
                self._progress(job_id, stages, "OCR", "completed")
            else:
                self._progress(job_id, stages, "OCR", "skipped")

            self.repository.save_document_pages(document_id, pages)
            document = self.repository.get_document(document_id)
            if document is None:
                raise KeyError("Uploaded document disappeared during ingestion")

            self._progress(job_id, stages, "EXTRACT", "running")
            events, cached = self._extract_verified(pages, sha256=str(document["sha256"]))
            self._progress(job_id, stages, "EXTRACT", "completed", cached=cached)
            self._progress(job_id, stages, "VERIFY", "completed", cached=cached)

            chunk_rows: list[dict[str, object]] = []
            texts: list[str] = []
            for page in pages:
                text = str(page["recovered_text"] or page["raw_text"])
                for index, chunk in enumerate(chunk_page_text(text)):
                    texts.append(chunk)
                    chunk_rows.append(
                        {
                            "id": f"chunk-{document_id}-{page['page_number']}-{index}",
                            "document_id": document_id,
                            "page_number": page["page_number"],
                            "chunk_index": index,
                            "text": chunk,
                        }
                    )

            self._progress(job_id, stages, "INDEX", "running", cached=cached)
            embedding_metadata: dict[str, str | int]
            if cached:
                try:
                    embeddings = self.embeddings.embed_documents(
                        str(document["title"]), texts
                    )
                    embedding_metadata = self.embeddings.metadata
                except (ProviderUnavailableError, ProviderResponseError):
                    formatted = [
                        self.embeddings.format_document(str(document["title"]), text)
                        for text in texts
                    ]
                    embeddings = [
                        deterministic_embedding(
                            text, dimensions=self.settings.gemini_embedding_dim
                        )
                        for text in formatted
                    ]
                    embedding_metadata = {
                        "embedding_provider": "demo-cache",
                        "embedding_model": "deterministic-token-hash-v1",
                        "embedding_dimension": self.settings.gemini_embedding_dim,
                    }
            else:
                embeddings = self.embeddings.embed_documents(
                    str(document["title"]), texts
                )
                embedding_metadata = self.embeddings.metadata
            if len(embeddings) != len(chunk_rows):
                raise ValueError("Embedding count does not match the chunk count")
            for row, embedding in zip(chunk_rows, embeddings, strict=True):
                row["embedding"] = embedding
                row.update(embedding_metadata)

            formation_ids = {
                str(interval["formation_name"]).casefold(): interval["formation_id"]
                for interval in self.repository.list_formation_intervals()
            }
            now = datetime.now(timezone.utc)
            event_rows = []
            for index, event in enumerate(events, start=1):
                event_rows.append(
                    {
                        "id": f"event-{document_id.removeprefix('document-')}-{index}",
                        "well_id": document["well_id"],
                        "formation_id": (
                            formation_ids[event.formation.casefold()]
                            if event.formation is not None
                            else None
                        ),
                        "hazard_type": event.hazard_type,
                        "start_md_m": event.start_md_m,
                        "end_md_m": event.end_md_m,
                        "severity": event.severity,
                        "description": event.description,
                        "historical_response": event.historical_response,
                        "extraction_confidence": event.confidence,
                        "source": "CACHED_VERIFIED" if cached else "AI_EXTRACTED",
                        "created_at": now,
                        "page_number": event.page_number,
                        "evidence_text": event.evidence_text,
                    }
                )

            stages["INDEX"] = "completed"
            self.repository.persist_ingestion_result(
                document_id=document_id,
                job_id=job_id,
                pages=pages,
                chunks=chunk_rows,
                events=event_rows,
                stages=stages,
                cached_verified_extraction=cached,
            )
        except Exception as error:
            active = next(
                (name for name in STAGE_NAMES if stages[name] == "running"), "EXTRACT"
            )
            stages[active] = "failed"
            self.repository.update_ingestion_job(
                job_id,
                status="failed",
                stages=stages,
                error_message=str(error),
                cached_verified_extraction=cached,
            )
        result = self.repository.get_ingestion_job(job_id)
        if result is None:
            raise KeyError(f"Ingestion job {job_id} was not found")
        return result
