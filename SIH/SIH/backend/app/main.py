from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.container import AppContainer
from app.ai import GeminiAIProvider, ProviderUnavailableError
from app.db import initialize_runtime_data
from app.routers import copilot, demo, documents, events, knowledge, system
from app.routers import telemetry, wells
from app.services.evidence_service import EvidenceService
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.copilot_service import CopilotService
from app.services.retrieval_service import RetrievalService
from app.services.risk_service import RiskService
from app.services.telemetry_service import TelemetryReplayService


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        repository, storage, runtime_settings, data_fallback_reason = (
            initialize_runtime_data(resolved_settings)
        )
        try:
            ai_provider = GeminiAIProvider(runtime_settings)
        except ProviderUnavailableError:
            ai_provider = None
        embedding_service = EmbeddingService(ai_provider, runtime_settings)
        embedding_service.invalidate_incompatible(repository)
        retrieval_service = RetrievalService(repository, embedding_service)
        application.state.container = AppContainer(
            settings=runtime_settings,
            configured_data_backend=resolved_settings.data_backend,
            data_fallback_reason=data_fallback_reason,
            repository=repository,
            telemetry=TelemetryReplayService(
                runtime_settings.telemetry_fixture_path
            ),
            risk=RiskService(
                lookahead_window_m=runtime_settings.lookahead_window_m,
                watch_threshold=runtime_settings.watch_threshold,
                elevated_threshold=runtime_settings.elevated_threshold,
                live_corroboration_threshold=(
                    runtime_settings.live_corroboration_threshold
                ),
            ),
            storage=storage,
            evidence=EvidenceService(repository, storage),
            ingestion=IngestionService(
                repository, storage, runtime_settings, ai_provider
            ),
            ai_provider=ai_provider,
            embedding=embedding_service,
            retrieval=retrieval_service,
            copilot=CopilotService(retrieval_service, ai_provider),
        )
        yield
        engine = getattr(repository, "engine", None)
        if engine is not None:
            engine.dispose()

    application = FastAPI(
        title="NWIS API",
        version="0.1.0",
        description="Evidence-backed formation-aware drilling intelligence.",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.frontend_origins,
        allow_origin_regex=resolved_settings.frontend_origin_regex,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    application.include_router(system.router, prefix="/api")
    application.include_router(demo.router, prefix="/api")
    application.include_router(wells.router, prefix="/api")
    application.include_router(events.router, prefix="/api")
    application.include_router(knowledge.router, prefix="/api")
    application.include_router(copilot.router, prefix="/api")
    application.include_router(documents.router, prefix="/api")
    application.include_router(telemetry.router, prefix="/api")
    return application


app = create_app()
