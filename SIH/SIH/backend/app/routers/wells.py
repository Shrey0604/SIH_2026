from collections import Counter
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.container import AppContainer
from app.dependencies import get_container
from app.services.analog_service import haversine_distance_km


router = APIRouter(tags=["wells"])


def _well_payloads(
    container: AppContainer, active_well_id: str, radius_km: float
) -> dict[str, Any]:
    wells = container.repository.list_wells()
    active = next((well for well in wells if well["id"] == active_well_id), None)
    if active is None:
        raise HTTPException(status_code=404, detail="Active well not found")
    intervals = container.repository.list_formation_intervals()
    events = container.repository.list_events()
    event_counts = Counter(event["well_id"] for event in events)
    result = []
    for well in wells:
        if not well["is_active"] and well["well_scope"] != "LOCAL_OFFSET":
            continue
        distance_km = haversine_distance_km(
            active["latitude"],
            active["longitude"],
            well["latitude"],
            well["longitude"],
        )
        if not well["is_active"] and distance_km > radius_km:
            continue
        well_intervals = [item for item in intervals if item["well_id"] == well["id"]]
        well_events = [item for item in events if item["well_id"] == well["id"]]
        result.append(
            {
                **well,
                "distance_km": round(distance_km, 3),
                "event_count": event_counts[well["id"]],
                "formations": well_intervals,
                "events": well_events,
                "hazards": sorted({item["hazard_type"] for item in well_events}),
            }
        )
    return {
        "active_well_id": active_well_id,
        "radius_km": radius_km,
        "wells": result,
        "synthetic_data": True,
    }


@router.get("/map/wells")
def list_map_wells(
    container: Annotated[AppContainer, Depends(get_container)],
) -> dict[str, Any]:
    wells = container.repository.list_wells()
    active = next(well for well in wells if well["is_active"])
    context_wells = []
    for well in wells:
        if well["well_scope"] != "CONTEXT":
            continue
        context_wells.append(
            {
                **well,
                "distance_km": round(
                    haversine_distance_km(
                        active["latitude"],
                        active["longitude"],
                        well["latitude"],
                        well["longitude"],
                    ),
                    1,
                ),
                "event_count": 0,
                "formations": [],
                "events": [],
                "hazards": [],
            }
        )
    local_count = sum(
        1
        for well in wells
        if not well["is_active"] and well["well_scope"] == "LOCAL_OFFSET"
    )
    return {
        "active_well_id": active["id"],
        "local_offset_count": local_count,
        "context_well_count": len(context_wells),
        "total_well_count": 1 + local_count + len(context_wells),
        "context_wells": context_wells,
        "synthetic_data": True,
    }


@router.get("/wells")
def list_wells(
    container: Annotated[AppContainer, Depends(get_container)],
    active_well_id: str = "active-01",
    radius_km: float = Query(default=5.0, gt=0, le=50),
) -> dict[str, Any]:
    return _well_payloads(container, active_well_id, radius_km)


@router.get("/wells/{well_id}")
def get_well(
    well_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
) -> dict[str, Any]:
    payload = _well_payloads(container, "active-01", 50)
    well = next((item for item in payload["wells"] if item["id"] == well_id), None)
    if well is None:
        raise HTTPException(status_code=404, detail="Well not found")
    return well


@router.get("/wells/{well_id}/formations")
def get_well_formations(
    well_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
) -> list[dict[str, Any]]:
    return [
        interval
        for interval in container.repository.list_formation_intervals()
        if interval["well_id"] == well_id
    ]


@router.get("/wells/{well_id}/events")
def get_well_events(
    well_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
) -> list[dict[str, Any]]:
    return [
        event
        for event in container.repository.list_events()
        if event["well_id"] == well_id
    ]
