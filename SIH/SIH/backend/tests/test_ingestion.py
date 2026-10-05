from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

import pymupdf
from pydantic import ValidationError

from app.ai import (
    ExtractedEvent,
    ExtractionResult,
    ProviderResponseError,
    ProviderUnavailableError,
)
from app.config import ROOT_DIR
from app.db import initialize_database
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService, MAX_PDF_BYTES
from app.services.pdf_service import chunk_page_text, extract_native_pages, text_quality
from app.storage.local import LocalStorageAdapter
from tests.helpers import sqlite_settings, temporary_directory


EVENT_TEXT = (
    "At 3210 m MD, partial circulation loss was observed while drilling the Barail "
    "interval. Returns reduced from 3210 m to 3218 m MD."
)


def make_pdf(text: str, *, scanned: bool = False) -> bytes:
    source = pymupdf.open()
    page = source.new_page()
    page.insert_textbox(pymupdf.Rect(50, 50, 540, 760), text, fontsize=11)
    if not scanned:
        return source.tobytes()
    image = page.get_pixmap(alpha=False).tobytes("png")
    source.close()
    scanned_document = pymupdf.open()
    scanned_page = scanned_document.new_page()
    scanned_page.insert_image(scanned_page.rect, stream=image)
    return scanned_document.tobytes()


class FakeProvider:
    provider_name = "gemini"
    embedding_model = "test-embedding"
    embedding_dimension = 3

    def __init__(self, *, invalid_evidence: bool = False):
        self.invalid_evidence = invalid_evidence
        self.vision_calls = 0
        self.extraction_calls = 0
        self.embedding_calls = 0

    def recover_scanned_page(self, image_png: bytes, *, page_number: int) -> str:
        self.vision_calls += 1
        assert image_png.startswith(b"\x89PNG")
        assert page_number == 1
        return EVENT_TEXT

    def extract_events(
        self,
        pages: list[dict[str, object]],
        *,
        validation_feedback: str | None = None,
    ) -> ExtractionResult:
        self.extraction_calls += 1
        del validation_feedback
        evidence = "This evidence was invented and is absent." if self.invalid_evidence else EVENT_TEXT
        return ExtractionResult(
            events=[
                ExtractedEvent(
                    hazard_type="MUD_LOSS",
                    formation="Barail",
                    start_md_m=3210,
                    end_md_m=3218,
                    severity="MEDIUM",
                    description="Partial circulation loss observed in the Barail interval.",
                    historical_response="Flow was reduced and the interval monitored.",
                    page_number=int(pages[0]["page_number"]),
                    evidence_text=evidence,
                    confidence=0.91,
                )
            ]
        )

    def generate_embedding(
        self, texts: list[str], *, task_type: str
    ) -> list[list[float]]:
        self.embedding_calls += 1
        self.last_embedding_task = task_type
        return [[1.0, 0.0, float(index)] for index, _text in enumerate(texts)]


class FailingProvider(FakeProvider):
    def extract_events(self, *args, **kwargs):
        del args, kwargs
        raise ProviderUnavailableError("Gemini is unavailable for this test")

    def generate_embedding(self, *args, **kwargs):
        del args, kwargs
        raise ProviderUnavailableError("Gemini embeddings are unavailable for this test")


class MalformedThenValidProvider(FakeProvider):
    def extract_events(self, pages, *, validation_feedback=None):
        self.extraction_calls += 1
        if self.extraction_calls == 1:
            raise ProviderResponseError("Malformed Gemini JSON")
        self.extraction_calls -= 1
        return super().extract_events(
            pages, validation_feedback=validation_feedback
        )


class IngestionTests(unittest.TestCase):
    def _service(self, root: Path, provider: FakeProvider | None):
        settings = sqlite_settings(root / "nwis.db", root / "storage")
        repository = initialize_database(settings)
        service = IngestionService(
            repository,
            LocalStorageAdapter(settings.local_storage_path),
            settings,
            provider,
        )
        return repository, service

    def test_upload_validation_rejects_wrong_type_and_oversize(self) -> None:
        with temporary_directory() as directory:
            _, service = self._service(Path(directory), FakeProvider())
            with self.assertRaisesRegex(ValueError, "Only PDF"):
                service.create_upload(
                    filename="notes.txt",
                    content_type="text/plain",
                    content=b"not a pdf",
                    document_type="DDR",
                )
            with self.assertRaisesRegex(ValueError, "20 MB"):
                service.create_upload(
                    filename="large.pdf",
                    content_type="application/pdf",
                    content=b"%PDF-" + b"0" * MAX_PDF_BYTES,
                    document_type="DDR",
                )

    def test_text_native_pdf_extracts_pages_and_chunks(self) -> None:
        pdf = make_pdf(EVENT_TEXT * 12)
        pages = extract_native_pages(pdf, "document-test")
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["extraction_method"], "NATIVE")
        chunks = chunk_page_text(str(pages[0]["raw_text"]))
        self.assertGreaterEqual(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 1_500 for chunk in chunks))
        self.assertGreater(text_quality(str(pages[0]["raw_text"])), 0.35)

    def test_scanned_page_uses_vision_recovery_fixture(self) -> None:
        with temporary_directory() as directory:
            provider = FakeProvider()
            repository, service = self._service(Path(directory), provider)
            pdf = make_pdf(EVENT_TEXT, scanned=True)
            created = service.create_upload(
                filename="scan.pdf",
                content_type="application/pdf",
                content=pdf,
                document_type="DDR",
            )
            job = service.process(
                str(created["ingestion_job_id"]), str(created["document_id"]), pdf
            )
            self.assertEqual(job["status"], "completed")
            self.assertEqual(job["stages"]["OCR"], "completed")
            self.assertEqual(provider.vision_calls, 1)
            self.assertEqual(len(job["events"]), 1)
            self.assertEqual(repository.counts()["document_pages"], 1)

    def test_unverified_evidence_cannot_create_event_records(self) -> None:
        with temporary_directory() as directory:
            provider = FakeProvider(invalid_evidence=True)
            repository, service = self._service(Path(directory), provider)
            initial_events = repository.counts()["events"]
            pdf = make_pdf(EVENT_TEXT)
            created = service.create_upload(
                filename="invalid-evidence.pdf",
                content_type="application/pdf",
                content=pdf,
                document_type="DDR",
            )
            job = service.process(
                str(created["ingestion_job_id"]), str(created["document_id"]), pdf
            )
            self.assertEqual(job["status"], "failed")
            self.assertEqual(provider.extraction_calls, 2)
            self.assertEqual(repository.counts()["events"], initial_events)
            self.assertEqual(repository.counts()["evidence"], initial_events)
            self.assertEqual(repository.counts()["document_pages"], 1)

    def test_malformed_model_output_gets_one_retry(self) -> None:
        with temporary_directory() as directory:
            provider = MalformedThenValidProvider()
            _, service = self._service(Path(directory), provider)
            pdf = make_pdf(EVENT_TEXT)
            created = service.create_upload(
                filename="retry.pdf",
                content_type="application/pdf",
                content=pdf,
                document_type="DDR",
            )
            job = service.process(
                str(created["ingestion_job_id"]), str(created["document_id"]), pdf
            )
            self.assertEqual(job["status"], "completed")
            self.assertEqual(provider.extraction_calls, 2)

    def test_valid_event_is_evidenced_searchable_and_hash_cached(self) -> None:
        with temporary_directory() as directory:
            provider = FakeProvider()
            repository, service = self._service(Path(directory), provider)
            pdf = make_pdf(EVENT_TEXT)
            created = service.create_upload(
                filename="valid.pdf",
                content_type="application/pdf",
                content=pdf,
                document_type="WCR",
            )
            job = service.process(
                str(created["ingestion_job_id"]), str(created["document_id"]), pdf
            )
            self.assertEqual(job["status"], "completed")
            self.assertEqual(job["events"][0]["evidence"][0]["page_number"], 1)
            chunks = repository.list_document_chunks(str(created["document_id"]))
            self.assertGreaterEqual(len(chunks), 1)
            results = repository.search_chunks(
                [1.0, 0.0, 0.0],
                provider="gemini",
                model="test-embedding",
                dimension=3,
            )
            self.assertEqual(results[0]["document_id"], created["document_id"])
            duplicate = service.create_upload(
                filename="renamed.pdf",
                content_type="application/pdf",
                content=pdf,
                document_type="DDR",
            )
            self.assertTrue(duplicate["duplicate"])
            self.assertEqual(
                duplicate["ingestion_job_id"], created["ingestion_job_id"]
            )
            self.assertEqual(provider.embedding_calls, 1)

    def test_strict_schema_rejects_unknown_hazard(self) -> None:
        with self.assertRaises(ValidationError):
            ExtractedEvent.model_validate(
                {
                    "hazard_type": "WASHOUT",
                    "formation": "Barail",
                    "start_md_m": 3210,
                    "end_md_m": 3218,
                    "severity": "MEDIUM",
                    "description": "Unsupported hazard should be rejected.",
                    "historical_response": None,
                    "page_number": 1,
                    "evidence_text": "Unsupported hazard should be rejected.",
                    "confidence": 0.5,
                }
            )

    def test_provider_failure_uses_cache_only_for_known_demo_hash(self) -> None:
        with temporary_directory() as directory:
            repository, service = self._service(Path(directory), FailingProvider())
            known_pdf = (ROOT_DIR / "demo_data" / "demo_report_barail.pdf").read_bytes()
            created = service.create_upload(
                filename="demo_report_barail.pdf",
                content_type="application/pdf",
                content=known_pdf,
                document_type="DDR",
            )
            job = service.process(
                str(created["ingestion_job_id"]),
                str(created["document_id"]),
                known_pdf,
            )
            self.assertEqual(job["status"], "completed")
            self.assertTrue(job["cached_verified_extraction"])
            self.assertEqual(job["events"][0]["source"], "CACHED_VERIFIED")
            chunks = repository.list_document_chunks(str(created["document_id"]))
            self.assertTrue(all(chunk["embedding_provider"] == "demo-cache" for chunk in chunks))

            event_count = repository.counts()["events"]
            unknown_pdf = make_pdf(EVENT_TEXT + " Unknown-file marker.")
            unknown = service.create_upload(
                filename="unknown.pdf",
                content_type="application/pdf",
                content=unknown_pdf,
                document_type="DDR",
            )
            failed = service.process(
                str(unknown["ingestion_job_id"]),
                str(unknown["document_id"]),
                unknown_pdf,
            )
            self.assertEqual(failed["status"], "failed")
            self.assertIn("Gemini is unavailable", failed["error_message"])
            self.assertEqual(repository.counts()["events"], event_count)

    def test_old_embedding_space_is_invalidated_and_rebuilt(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            settings = sqlite_settings(root / "nwis.db", root / "storage")
            repository = initialize_database(settings)
            provider = FakeProvider()
            service = IngestionService(
                repository,
                LocalStorageAdapter(settings.local_storage_path),
                settings,
                provider,
            )
            pdf = make_pdf(EVENT_TEXT)
            created = service.create_upload(
                filename="rebuild.pdf",
                content_type="application/pdf",
                content=pdf,
                document_type="DDR",
            )
            service.process(
                str(created["ingestion_job_id"]), str(created["document_id"]), pdf
            )

            next_settings = replace(settings, gemini_embedding_model="next-embedding")
            next_provider = FakeProvider()
            next_provider.embedding_model = "next-embedding"
            embeddings = EmbeddingService(next_provider, next_settings)
            self.assertGreaterEqual(embeddings.invalidate_incompatible(repository), 1)
            invalidated = repository.list_document_chunks(str(created["document_id"]))
            self.assertTrue(all(chunk["embedding"] is None for chunk in invalidated))

            rebuilt = embeddings.rebuild_missing(repository)
            self.assertEqual(rebuilt, len(invalidated))
            rebuilt_chunks = repository.list_document_chunks(str(created["document_id"]))
            self.assertTrue(
                all(chunk["embedding_model"] == "next-embedding" for chunk in rebuilt_chunks)
            )
            self.assertEqual(len(rebuilt_chunks[0]["embedding"]), 3)


if __name__ == "__main__":
    unittest.main()
