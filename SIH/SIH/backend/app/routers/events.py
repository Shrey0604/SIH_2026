from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.container import AppContainer
from app.dependencies import get_container


router = APIRouter(tags=["events"])


@router.get("/events")
def list_events(
    container: Annotated[AppContainer, Depends(get_container)],
    well_id: str | None = None,
    formation: str | None = None,
    hazard_type: str | None = None,
    q: str | None = Query(default=None, max_length=160),
) -> list[dict[str, Any]]:
    query = q.casefold().strip() if q else None
    result = []
    for event in container.repository.list_events():
        if well_id and event["well_id"] != well_id:
            continue
        if formation and (event["formation_name"] or "").casefold() != formation.casefold():
            continue
        if hazard_type and event["hazard_type"] != hazard_type:
            continue
        if query:
            searchable = " ".join(
                str(event.get(field) or "")
                for field in ("hazard_type", "formation_name", "description", "historical_response")
            ).casefold()
            if query not in searchable:
                continue
        result.append(event)
    return result


@router.get("/events/{event_id}")
def get_event(
    event_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
) -> dict[str, Any]:
    event = container.evidence.event_with_evidence(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/events/{event_id}/evidence")
def get_event_evidence(
    event_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
) -> list[dict[str, Any]]:
    if container.repository.get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return container.repository.list_event_evidence(event_id)
