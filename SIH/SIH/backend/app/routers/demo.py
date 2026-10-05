from typing import Annotated

from fastapi import APIRouter, Depends

from app.container import AppContainer
from app.dependencies import get_container
from app.schemas import DemoResetResponse


router = APIRouter(tags=["demo"])


@router.post("/demo/reset", response_model=DemoResetResponse)
def reset_demo(
    container: Annotated[AppContainer, Depends(get_container)],
) -> DemoResetResponse:
    container.telemetry.reset()
    container.repository.reset_runtime_data()
    counts = container.repository.counts()
    return DemoResetResponse(
        status="reset",
        replay=container.telemetry.snapshot(),
        runtime_alerts=counts["alerts"],
    )

