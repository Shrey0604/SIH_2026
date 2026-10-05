#!/usr/bin/env python3
"""Optional live Gemini integration check. Run with .env exported and PYTHONPATH=backend."""

from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pymupdf

from app.ai import GeminiAIProvider
from app.config import ROOT_DIR, Settings
from app.db import initialize_database
from app.services.embedding_service import EmbeddingService
from app.services.evidence_service import EvidenceService
from app.services.ingestion_service import IngestionService
from app.services.pdf_service import normalized_evidence
from app.storage import create_storage_adapter


def modified_demo_pdf() -> bytes:
    source = ROOT_DIR / "demo_data" / "demo_report_barail.pdf"
    document = pymupdf.open(source)
    try:
        marker = datetime.now(timezone.utc).isoformat()
        document[0].insert_text(
            pymupdf.Point(72, 790),
            f"Live Gemini verification copy: {marker}",
            fontsize=7,
            color=(0.25, 0.25, 0.25),
        )
        return document.tobytes(garbage=4, deflate=True)
    finally:
        document.close()


def main() -> None:
    environment_settings = Settings.from_env()
    if not environment_settings.gemini_api_key:
        raise SystemExit("GEMINI_API_KEY is not configured")

    temporary = tempfile.TemporaryDirectory(prefix="nwis-gemini-verification-")
    root = Path(temporary.name)
    settings = replace(
        environment_settings,
        data_backend="sqlite",
        database_url=f"sqlite:///{root / 'verification.db'}",
        local_storage_path=root / "storage",
    )

    provider = GeminiAIProvider(settings)
    repository = initialize_database(settings)
    storage = create_storage_adapter(settings)
    embeddings = EmbeddingService(provider, settings)

    invalidated = embeddings.invalidate_incompatible(repository)
    rebuilt = embeddings.rebuild_missing(repository)

    pdf_bytes = modified_demo_pdf()
    ingestion = IngestionService(repository, storage, settings, provider)
    created = ingestion.create_upload(
        filename="demo_report_barail_live_gemini.pdf",
        content_type="application/pdf",
        content=pdf_bytes,
        document_type="DDR",
    )
    if created["duplicate"]:
        raise RuntimeError("The live verification PDF unexpectedly hit the hash cache")
    job = ingestion.process(
        str(created["ingestion_job_id"]), str(created["document_id"]), pdf_bytes
    )
    if job["status"] != "completed":
        raise RuntimeError(f"Live ingestion failed: {job['error_message']}")
    if job["cached_verified_extraction"]:
        raise RuntimeError("Live verification unexpectedly used the verified demo cache")
    if not job["events"]:
        raise RuntimeError("Live Gemini extraction returned no validated event")

    event = next(
        (
            candidate
            for candidate in job["events"]
            if candidate["hazard_type"] == "MUD_LOSS"
            and candidate["formation_name"] == "Barail"
        ),
        None,
    )
    if event is None:
        raise RuntimeError("Expected Barail MUD_LOSS event was not returned")
    evidence = event["evidence"][0]
    if evidence["page_number"] != 2:
        raise RuntimeError("Expected event evidence on page 2")

    pages = ingestion.repository.list_document_chunks(str(created["document_id"]))
    page_two = next(chunk for chunk in pages if chunk["page_number"] == 2)
    if normalized_evidence(evidence["evidence_text"]) not in normalized_evidence(
        page_two["text"]
    ):
        raise RuntimeError("Live evidence text is not supported by cited page 2")
    if not pages or any(
        len(chunk["embedding"] or []) != settings.gemini_embedding_dim for chunk in pages
    ):
        raise RuntimeError("Persisted Gemini embeddings have an unexpected dimension")
    if any(chunk["embedding_provider"] != "gemini" for chunk in pages):
        raise RuntimeError("Non-Gemini vectors were stored in the live document")

    page_png, _document = EvidenceService(repository, storage).render_page_png(
        str(created["document_id"]), 2
    )
    if not page_png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("The exact source page did not render as PNG")

    query = "What mud-loss event occurred in the Barail interval near 3210 m?"
    matches = embeddings.search(repository, query, top_k=6)
    match = next(
        (
            result
            for result in matches
            if "barail" in result["text"].casefold()
            and "loss" in result["text"].casefold()
        ),
        None,
    )
    if match is None:
        raise RuntimeError("Similarity search did not retrieve a Barail mud-loss chunk")

    source_id = f"{evidence['document_id']}:p{evidence['page_number']}"
    answer = provider.generate_answer(
        question="What happened in the Barail interval and what response was observed?",
        live_context={
            "active_well": "NWIS-ACT-01",
            "formation": "Barail",
            "current_md_m": 3287.0,
        },
        evidence_bundle=[
            {
                "source_id": source_id,
                "event": event["description"],
                "historical_response": event["historical_response"],
                "evidence_text": evidence["evidence_text"],
                "page_number": evidence["page_number"],
            }
        ],
    )
    if set(answer.source_ids) - {source_id}:
        raise RuntimeError("Gemini answer returned an invented citation")

    print(
        json.dumps(
            {
                "models": {
                    "extraction": settings.gemini_extraction_model,
                    "copilot": settings.gemini_copilot_model,
                    "embedding": settings.gemini_embedding_model,
                    "embedding_dimension": settings.gemini_embedding_dim,
                },
                "migration": {
                    "invalidated_vectors": invalidated,
                    "rebuilt_vectors": rebuilt,
                },
                "event": event,
                "verified_cache_bypassed": True,
                "persisted_chunk_count": len(pages),
                "source_page": {
                    "page_number": 2,
                    "content_type": "image/png",
                    "rendered_bytes": len(page_png),
                },
                "similarity_result": {
                    "document_id": match["document_id"],
                    "page_number": match["page_number"],
                    "similarity": match["similarity"],
                    "text": match["text"],
                },
                "grounded_answer": answer.model_dump(),
            },
            indent=2,
        )
    )
    engine = getattr(repository, "engine", None)
    if engine is not None:
        engine.dispose()
    temporary.cleanup()


if __name__ == "__main__":
    main()
