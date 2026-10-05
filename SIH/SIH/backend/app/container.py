from dataclasses import dataclass

from app.ai import AIProvider
from app.config import Settings
from app.repositories.base import Repository
from app.services.evidence_service import EvidenceService
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.copilot_service import CopilotService
from app.services.retrieval_service import RetrievalService
from app.services.risk_service import RiskService
from app.services.telemetry_service import TelemetryReplayService
from app.storage.base import StorageAdapter


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    repository: Repository
    telemetry: TelemetryReplayService
    risk: RiskService
    storage: StorageAdapter
    evidence: EvidenceService
    ingestion: IngestionService | None = None
    ai_provider: AIProvider | None = None
    embedding: EmbeddingService | None = None
    retrieval: RetrievalService | None = None
    copilot: CopilotService | None = None
    configured_data_backend: str | None = None
    data_fallback_reason: str | None = None
