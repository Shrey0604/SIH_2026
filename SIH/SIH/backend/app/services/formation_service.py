from __future__ import annotations

from typing import Any


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def normalized_formation_position(
    md_m: float, top_md_m: float, base_md_m: float
) -> float:
    if base_md_m <= top_md_m:
        raise ValueError("Formation base must be deeper than its top")
    return clamp01((md_m - top_md_m) / (base_md_m - top_md_m))


def find_formation_at_depth(
    intervals: list[dict[str, Any]], md_m: float
) -> dict[str, Any] | None:
    ordered = sorted(intervals, key=lambda interval: interval["top_md_m"])
    for index, interval in enumerate(ordered):
        is_last = index == len(ordered) - 1
        if interval["top_md_m"] <= md_m < interval["base_md_m"] or (
            is_last and md_m == interval["base_md_m"]
        ):
            return {
                **interval,
                "normalized_position": normalized_formation_position(
                    md_m, interval["top_md_m"], interval["base_md_m"]
                ),
            }
    return None

