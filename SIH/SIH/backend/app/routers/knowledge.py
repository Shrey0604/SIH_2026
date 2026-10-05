from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.container import AppContainer
from app.dependencies import get_container


router = APIRouter(tags=["knowledge"])


@router.get("/knowledge/search")
def search_knowledge(
    container: Annotated[AppContainer, Depends(get_container)],
    q: str | None = Query(default=None, max_length=160),
    well_id: str | None = None,
    formation: str | None = None,
    hazard_type: str | None = None,
) -> dict[str, Any]:
    results = container.retrieval.search_events(
        query=q,
        well_id=well_id,
        formation=formation,
        hazard_type=hazard_type,
    )
    return {
        "query": q or "",
        "filters": {
            "well_id": well_id,
            "formation": formation,
            "hazard_type": hazard_type,
        },
        "result_count": len(results),
        "results": results,
    }
