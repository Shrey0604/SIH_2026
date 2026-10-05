#!/usr/bin/env python3
"""Run the Phase 8 deterministic demo chain five times against live servers."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from typing import Any


API = os.getenv("NWIS_SMOKE_API", "http://127.0.0.1:8000")
FRONTEND = os.getenv("NWIS_SMOKE_FRONTEND", "http://127.0.0.1:5173")
QUESTION = "What happened in nearby wells in the Barail interval ahead of us?"


def request(path: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> tuple[Any, str]:
    payload = json.dumps(body).encode() if body is not None else None
    target = f"{API}{path}" if path.startswith("/api/") else f"{FRONTEND}{path}"
    req = urllib.request.Request(
        target,
        method=method,
        data=payload,
        headers={"Content-Type": "application/json"} if payload else {},
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        return json.loads(raw), content_type
    return raw, content_type


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_once(run_number: int) -> dict[str, Any]:
    request("/api/demo/reset", method="POST")
    clear, _ = request("/api/telemetry/active-01/current?radius_km=5")
    check(clear["state"] == "CLEAR" and clear["replay"]["sequence"] == 0, "reset was not Clear at sequence 0")

    page, content_type = request("/live")
    check("text/html" in content_type and b'id="root"' in page, "/live did not render the app shell")

    wells, _ = request("/api/wells?active_well_id=active-01&radius_km=5")
    selected = next((well for well in wells["wells"] if well["id"] == "off-03"), None)
    check(selected is not None and selected["name"] == "NWIS-OFF-03", "NWIS-OFF-03 could not be selected")

    request(
        "/api/telemetry/active-01/control?radius_km=5",
        method="POST",
        body={"action": "start"},
    )
    first_watch = None
    first_elevated = None
    elevated_payload = None
    for _ in range(1, 70):
        payload, _ = request("/api/telemetry/active-01/next?radius_km=5")
        if payload["state"] == "WATCH" and first_watch is None:
            first_watch = payload
        if payload["state"] == "ELEVATED":
            first_elevated = payload
            elevated_payload = payload
            break
    check(first_watch is not None, "Watch was not reached")
    check(first_elevated is not None and elevated_payload is not None, "Elevated was not reached")
    check(first_watch["replay"]["sequence"] == 10, "Watch timing changed")
    check(first_elevated["replay"]["sequence"] == 40, "Elevated timing changed")

    hazard = elevated_payload["active_hazard"]
    check(hazard and len(hazard["analogs"]) >= 3, "alert explanation has insufficient analog support")
    supporting_ids = sorted({event["well_id"] for event in hazard["analogs"]})
    event_id = next(event["id"] for event in hazard["analogs"] if event["well_id"] == "off-03")
    event, _ = request(f"/api/events/{event_id}")
    check(event["evidence"], "selected historical event has no evidence")
    evidence = event["evidence"][0]
    source_page, page_type = request(
        f"/api/documents/{evidence['document_id']}/page/{evidence['page_number']}"
    )
    check(page_type.startswith("image/png") and len(source_page) > 1_000, "exact source page did not render")

    copilot, _ = request(
        "/api/copilot/query",
        method="POST",
        body={
            "question": QUESTION,
            "active_well_id": "active-01",
            "current_md_m": elevated_payload["sample"]["md_m"],
            "formation": elevated_payload["current_formation"]["formation_name"],
            "selected_well_ids": supporting_ids,
        },
    )
    check(not copilot["insufficient_evidence"], "scripted copilot question returned insufficient evidence")
    check(len(copilot["sources"]) >= 2, "copilot returned fewer than two clickable sources")
    check(
        all(source["source_id"] in copilot["answer_markdown"] for source in copilot["sources"]),
        "copilot answer omitted an inline source citation",
    )

    request("/api/demo/reset", method="POST")
    final, _ = request("/api/telemetry/active-01/current?radius_km=5")
    check(final["state"] == "CLEAR" and final["replay"]["sequence"] == 0, "final reset failed")
    return {
        "run": run_number,
        "watch": {"sequence": 10, "md_m": first_watch["sample"]["md_m"]},
        "elevated": {"sequence": 40, "md_m": first_elevated["sample"]["md_m"]},
        "event": event_id,
        "source_page": f"{evidence['filename']} p.{evidence['page_number']}",
        "copilot_mode": copilot["generation_mode"],
        "citations": len(copilot["sources"]),
        "reset": "CLEAR@0",
    }


def main() -> int:
    results = []
    try:
        for run_number in range(1, 6):
            result = run_once(run_number)
            results.append(result)
            print(json.dumps(result), flush=True)
    except Exception as error:  # noqa: BLE001 - smoke runner must print a concise failure
        print(json.dumps({"status": "failed", "completed": len(results), "error": str(error)}))
        return 1
    print(json.dumps({"status": "passed", "runs": len(results), "clean_runs": "5/5"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

