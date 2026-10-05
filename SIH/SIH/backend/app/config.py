from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_sqlite_url(url: str) -> str:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url
    path = url[len(prefix) :]
    if path == ":memory:" or Path(path).is_absolute():
        return url
    return f"{prefix}{(ROOT_DIR / path).resolve()}"


def _positive_int(value: str, name: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return parsed


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str
    demo_mode: bool
    frontend_origin: str
    data_backend: str
    database_url: str
    supabase_url: str | None
    supabase_service_role_key: str | None
    supabase_storage_bucket: str
    local_storage_path: Path
    gemini_api_key: str | None
    gemini_extraction_model: str
    gemini_copilot_model: str
    gemini_embedding_model: str
    gemini_embedding_dim: int
    lookahead_window_m: float
    watch_threshold: float
    elevated_threshold: float
    live_corroboration_threshold: float
    telemetry_fixture_path: Path
    seed_fixture_path: Path
    # Optional regex for extra browser origins, e.g. Vercel preview deployments.
    frontend_origin_regex: str | None = None

    @property
    def frontend_origins(self) -> list[str]:
        """FRONTEND_ORIGIN accepts a comma-separated list of exact origins."""
        return [
            origin.strip().rstrip("/")
            for origin in self.frontend_origin.split(",")
            if origin.strip()
        ]

    @classmethod
    def from_env(cls) -> "Settings":
        data_backend = os.getenv("DATA_BACKEND", "sqlite").strip().lower()
        if data_backend not in {"sqlite", "supabase"}:
            raise ValueError("DATA_BACKEND must be 'sqlite' or 'supabase'")

        default_url = "sqlite:///./backend/data/nwis.db"
        database_url = _resolve_sqlite_url(os.getenv("DATABASE_URL", default_url))
        if data_backend == "supabase" and database_url.startswith("sqlite"):
            raise ValueError("DATA_BACKEND=supabase requires a PostgreSQL DATABASE_URL")

        local_storage = Path(os.getenv("LOCAL_STORAGE_PATH", "backend/data/storage"))
        if not local_storage.is_absolute():
            local_storage = ROOT_DIR / local_storage

        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            demo_mode=_as_bool(os.getenv("DEMO_MODE"), default=True),
            frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
            data_backend=data_backend,
            database_url=database_url,
            supabase_url=os.getenv("SUPABASE_URL") or None,
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY") or None,
            supabase_storage_bucket=os.getenv(
                "SUPABASE_STORAGE_BUCKET", "nwis-documents"
            ),
            local_storage_path=local_storage.resolve(),
            gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
            gemini_extraction_model=os.getenv(
                "GEMINI_EXTRACTION_MODEL", "gemini-3.5-flash"
            ),
            gemini_copilot_model=os.getenv(
                "GEMINI_COPILOT_MODEL", "gemini-3.5-flash"
            ),
            gemini_embedding_model=os.getenv(
                "GEMINI_EMBEDDING_MODEL", "gemini-embedding-2"
            ),
            gemini_embedding_dim=_positive_int(
                os.getenv("GEMINI_EMBEDDING_DIM", "768"), "GEMINI_EMBEDDING_DIM"
            ),
            lookahead_window_m=float(os.getenv("LOOKAHEAD_WINDOW_M", "150")),
            watch_threshold=float(os.getenv("WATCH_THRESHOLD", "0.45")),
            elevated_threshold=float(os.getenv("ELEVATED_THRESHOLD", "0.65")),
            live_corroboration_threshold=float(
                os.getenv("LIVE_CORROBORATION_THRESHOLD", "0.50")
            ),
            telemetry_fixture_path=ROOT_DIR / "demo_data" / "telemetry_scenario.csv",
            seed_fixture_path=ROOT_DIR / "demo_data" / "demo_seed.json",
            frontend_origin_regex=os.getenv("FRONTEND_ORIGIN_REGEX") or None,
        )
