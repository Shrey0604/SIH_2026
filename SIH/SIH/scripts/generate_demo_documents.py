from __future__ import annotations

import json
from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demo_data"


def page_text(event: dict[str, object], page_number: int) -> str:
    if page_number != event["page"]:
        return (
            f"Daily operational record — page {page_number}\n\n"
            "Routine drilling observations were recorded for this interval. "
            "See the cited event page for the structured incident evidence."
        )
    end_depth = event.get("end_md_m")
    depth = (
        f'{float(event["start_md_m"]):.0f}–{float(end_depth):.0f} m MD'
        if end_depth is not None
        else f'{float(event["start_md_m"]):.0f} m MD'
    )
    response = event.get("historical_response") or "No response was explicitly recorded."
    return (
        f'Formation: {event["formation"]}\n'
        f"Depth interval: {depth}\n"
        f'Hazard: {str(event["hazard_type"]).replace("_", " ")}\n'
        f'Severity: {event["severity"]}\n\n'
        f'{event["description"]}\n\n'
        f"Historical response observed: {response}"
    )


def build_document(filename: str, events: list[dict[str, object]]) -> None:
    path = DEMO_DIR / filename
    page_count = max(int(event["page"]) for event in events)
    pdf = pymupdf.open()
    pdf.set_metadata(
        {
            "title": filename.removesuffix(".pdf").replace("_", " "),
            "author": "NWIS synthetic demo fixture",
            "subject": "Synthetic engineering demo report — not operational data",
            "creationDate": "D:20250101000000+00'00'",
            "modDate": "D:20250101000000+00'00'",
        }
    )
    event_by_page = {int(event["page"]): event for event in events}
    for page_number in range(1, page_count + 1):
        page = pdf.new_page(width=595, height=842)
        page.insert_text((48, 52), "NWIS — SYNTHETIC ENGINEERING DEMO REPORT", fontsize=10)
        page.insert_text((48, 72), "Not Oil India operational data", fontsize=8, color=(0.35, 0.4, 0.43))
        event = event_by_page.get(page_number, events[0])
        page.insert_text((48, 104), f'Well: {event["well"]}', fontsize=12)
        page.insert_textbox(
            pymupdf.Rect(48, 132, 547, 742),
            page_text(event, page_number),
            fontsize=11,
            lineheight=1.35,
            color=(0.08, 0.1, 0.11),
        )
        page.insert_text((48, 800), f"Page {page_number} of {page_count}", fontsize=8)
    pdf.save(path, garbage=4, deflate=True)
    pdf.close()


def main() -> None:
    fixture = json.loads((DEMO_DIR / "demo_seed.json").read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, object]]] = {}
    for event in fixture["events"]:
        grouped.setdefault(event["document"], []).append(event)
    for filename, events in grouped.items():
        build_document(filename, events)
        print(f"generated {filename}")


if __name__ == "__main__":
    main()
