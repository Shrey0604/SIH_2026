from typing import Any, Literal

from pydantic import BaseModel


class ReplaySnapshot(BaseModel):
    status: str
    sequence: int
    sample: dict[str, Any]
    sample_count: int


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]
    data_backend: Literal["sqlite", "supabase"]
    configured_data_backend: Literal["sqlite", "supabase"]
    data_fallback_reason: str | None
    demo_mode: bool
    gemini_configured: bool


class DemoResetResponse(BaseModel):
    status: Literal["reset"]
    replay: ReplaySnapshot
    runtime_alerts: int
