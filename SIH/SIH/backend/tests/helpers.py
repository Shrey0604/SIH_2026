import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from app.config import ROOT_DIR, Settings
from app.repositories import sqlalchemy_repository


def sqlite_settings(database_path: Path, storage_path: Path) -> Settings:
    return Settings(
        app_env="test",
        demo_mode=True,
        frontend_origin="http://localhost:5173",
        data_backend="sqlite",
        database_url=f"sqlite:///{database_path}",
        supabase_url=None,
        supabase_service_role_key=None,
        supabase_storage_bucket="nwis-documents",
        local_storage_path=storage_path,
        gemini_api_key=None,
        gemini_extraction_model="test-extraction",
        gemini_copilot_model="test-copilot",
        gemini_embedding_model="test-embedding",
        gemini_embedding_dim=3,
        lookahead_window_m=150.0,
        watch_threshold=0.45,
        elevated_threshold=0.65,
        live_corroboration_threshold=0.50,
        telemetry_fixture_path=ROOT_DIR / "demo_data" / "telemetry_scenario.csv",
        seed_fixture_path=ROOT_DIR / "demo_data" / "demo_seed.json",
    )


@contextmanager
def temporary_directory() -> Iterator[str]:
    """A temporary directory whose SQLite engines are disposed before it is removed.

    Pooled SQLite connections keep the database file open; Windows refuses to
    delete an open file, so every engine created inside the block is disposed first.
    """
    engines = []
    create_engine = sqlalchemy_repository.create_engine

    def tracking_create_engine(*args, **kwargs):
        engine = create_engine(*args, **kwargs)
        engines.append(engine)
        return engine

    with patch.object(sqlalchemy_repository, "create_engine", tracking_create_engine):
        with tempfile.TemporaryDirectory() as directory:
            try:
                yield directory
            finally:
                for engine in engines:
                    engine.dispose()
