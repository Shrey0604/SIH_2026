from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.container import AppContainer
from app.dependencies import get_container


router = APIRouter(tags=["copilot"])


class CopilotQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=500)
    active_well_id: str = Field(default="active-01", max_length=64)
    current_md_m: float | None = Field(default=None, ge=0, le=20_000)
    formation: str | None = Field(default=None, max_length=80)
    selected_well_ids: list[str] = Field(default_factory=list, max_length=10)


@router.post("/copilot/query")
def query_copilot(
    request: CopilotQuery,
    container: Annotated[AppContainer, Depends(get_container)],
) -> dict[str, Any]:
    active_well = next(
        (
            well
            for well in container.repository.list_wells()
            if well["id"] == request.active_well_id
        ),
        None,
    )
    live_context: dict[str, object] = {
        "active_well_id": request.active_well_id,
        "active_well_name": active_well["name"] if active_well else request.active_well_id,
        "current_md_m": request.current_md_m,
        "formation": request.formation,
    }
    return container.copilot.query(
        question=request.question,
        live_context=live_context,
        selected_well_ids=request.selected_well_ids,
    )
