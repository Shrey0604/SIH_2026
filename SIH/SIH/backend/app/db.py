from dataclasses import replace

from app.config import Settings
from app.repositories import create_repository
from app.repositories.base import Repository
from app.services.seed_service import SeedService
from app.storage import create_storage_adapter
from app.storage.base import StorageAdapter


def initialize_database(settings: Settings) -> Repository:
    repository = create_repository(settings)
    SeedService(repository, settings.seed_fixture_path).initialize()
    return repository


def initialize_runtime_data(
    settings: Settings,
) -> tuple[Repository, StorageAdapter, Settings, str | None]:
    """Initialize the selected data layer, with an explicit demo-only local fallback."""
    repository: Repository | None = None
    try:
        repository = initialize_database(settings)
        storage = create_storage_adapter(settings)
        return repository, storage, settings, None
    except Exception:
        if settings.data_backend != "supabase" or not settings.demo_mode:
            raise
        engine = getattr(repository, "engine", None)
        if engine is not None:
            engine.dispose()
        fallback_database = settings.local_storage_path.parent / "nwis-fallback.db"
        fallback_settings = replace(
            settings,
            data_backend="sqlite",
            database_url=f"sqlite:///{fallback_database}",
        )
        fallback_repository = initialize_database(fallback_settings)
        fallback_storage = create_storage_adapter(fallback_settings)
        return (
            fallback_repository,
            fallback_storage,
            fallback_settings,
            "Hosted Supabase data layer unavailable; using local SQLite and file storage.",
        )
