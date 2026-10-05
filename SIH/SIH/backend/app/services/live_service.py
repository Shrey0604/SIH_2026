from __future__ import annotations

from typing import Any

from app.container import AppContainer


ACTIVE_WELL_ID = "active-01"


def build_live_payload(
    container: AppContainer, selected_radius_km: float = 5.0
) -> dict[str, Any]:
    wells = container.repository.list_wells()
    active_well = next(well for well in wells if well["id"] == ACTIVE_WELL_ID)
    sample = container.telemetry.current_sample()
    replay = container.telemetry.snapshot()
    result = container.risk.evaluate(
        sample=sample,
        history=container.telemetry.history_through(sample.seq),
        active_well=active_well,
        wells=wells,
        intervals=container.repository.list_formation_intervals(),
        events=container.repository.list_events(),
        selected_radius_km=selected_radius_km,
        replay_status=replay["status"],
    )
    return {
        "type": "telemetry",
        "replay": replay,
        "active_well": active_well,
        **result,
    }

