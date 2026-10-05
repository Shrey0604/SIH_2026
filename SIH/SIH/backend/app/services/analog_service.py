from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from app.services.formation_service import clamp01, normalized_formation_position


EARTH_RADIUS_KM = 6371.0088


def event_midpoint(start_md_m: float, end_md_m: float | None) -> float:
    return start_md_m if end_md_m is None else (start_md_m + end_md_m) / 2.0


def project_event_depth(
    event_start_md_m: float,
    event_end_md_m: float | None,
    offset_top_md_m: float,
    offset_base_md_m: float,
    active_top_md_m: float,
    active_base_md_m: float,
) -> tuple[float, float]:
    relative_position = normalized_formation_position(
        event_midpoint(event_start_md_m, event_end_md_m),
        offset_top_md_m,
        offset_base_md_m,
    )
    projected_md_m = active_top_md_m + relative_position * (
        active_base_md_m - active_top_md_m
    )
    return relative_position, projected_md_m


def haversine_distance_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    lat_a = radians(latitude_a)
    lat_b = radians(latitude_b)
    delta_lat = lat_b - lat_a
    delta_lon = radians(longitude_b - longitude_a)
    haversine = sin(delta_lat / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin(
        delta_lon / 2
    ) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(haversine))


def spatial_score(distance_km: float, selected_radius_km: float) -> float:
    if selected_radius_km <= 0:
        raise ValueError("Selected radius must be positive")
    return clamp01(1.0 - distance_km / selected_radius_km)


def lookahead_proximity_score(lookahead_m: float, window_m: float) -> float:
    if window_m <= 0:
        raise ValueError("Look-ahead window must be positive")
    return clamp01(1.0 - lookahead_m / window_m)


def evidence_quality_score(
    extraction_confidence: float, has_exact_page_evidence: bool
) -> float:
    return clamp01(
        0.70 * clamp01(extraction_confidence)
        + 0.30 * float(has_exact_page_evidence)
    )


def analog_relevance_score(
    formation_match: bool,
    spatial: float,
    proximity: float,
    evidence_quality: float,
) -> float:
    return clamp01(
        0.45 * float(formation_match)
        + 0.20 * clamp01(spatial)
        + 0.20 * clamp01(proximity)
        + 0.15 * clamp01(evidence_quality)
    )

