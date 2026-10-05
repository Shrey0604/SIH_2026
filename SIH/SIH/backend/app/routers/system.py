from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.container import AppContainer
from app.dependencies import get_container
from app.schemas import HealthResponse


router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(
    response: Response,
    container: Annotated[AppContainer, Depends(get_container)],
) -> HealthResponse:
    database_ok = container.repository.health_check()
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ok" if database_ok and not container.data_fallback_reason else "degraded",
        database="ok" if database_ok else "unavailable",
        data_backend=container.settings.data_backend,
        configured_data_backend=container.configured_data_backend or container.settings.data_backend,
        data_fallback_reason=container.data_fallback_reason,
        demo_mode=container.settings.demo_mode,
        gemini_configured=bool(container.settings.gemini_api_key),
    )
