from __future__ import annotations

import asyncio
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.container import AppContainer
from app.dependencies import get_container
from app.services.live_service import ACTIVE_WELL_ID, build_live_payload


router = APIRouter(tags=["telemetry"])


class ReplayControl(BaseModel):
    action: Literal["start", "pause", "resume", "reset"]


def _apply_action(container: AppContainer, action: str) -> None:
    if action == "start":
        container.telemetry.start()
    elif action == "pause":
        container.telemetry.pause()
    elif action == "resume":
        container.telemetry.resume()
    elif action == "reset":
        container.telemetry.reset()
        container.repository.reset_runtime_data()
    else:
        raise HTTPException(status_code=422, detail="Unknown replay action")


@router.get("/telemetry/{well_id}/current")
def current_telemetry(
    well_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
    radius_km: float = Query(default=5.0, gt=0, le=50),
) -> dict[str, Any]:
    if well_id != ACTIVE_WELL_ID:
        raise HTTPException(status_code=404, detail="Replay well not found")
    return build_live_payload(container, radius_km)


@router.get("/telemetry/{well_id}/next")
def next_telemetry(
    well_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
    radius_km: float = Query(default=5.0, gt=0, le=50),
) -> dict[str, Any]:
    if well_id != ACTIVE_WELL_ID:
        raise HTTPException(status_code=404, detail="Replay well not found")
    container.telemetry.advance()
    return build_live_payload(container, radius_km)


@router.post("/telemetry/{well_id}/control")
def control_telemetry(
    well_id: str,
    control: ReplayControl,
    container: Annotated[AppContainer, Depends(get_container)],
    radius_km: float = Query(default=5.0, gt=0, le=50),
) -> dict[str, Any]:
    if well_id != ACTIVE_WELL_ID:
        raise HTTPException(status_code=404, detail="Replay well not found")
    _apply_action(container, control.action)
    return build_live_payload(container, radius_km)


@router.websocket("/ws/telemetry/{well_id}")
async def telemetry_socket(
    websocket: WebSocket,
    well_id: str,
    radius_km: float = 5.0,
) -> None:
    if well_id != ACTIVE_WELL_ID or not 0 < radius_km <= 50:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    container: AppContainer = websocket.app.state.container
    await websocket.send_json(build_live_payload(container, radius_km))
    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_json(), timeout=1.0
                )
                _apply_action(container, str(message.get("action", "")))
            except TimeoutError:
                container.telemetry.advance()
            await websocket.send_json(build_live_payload(container, radius_km))
    except WebSocketDisconnect:
        return
