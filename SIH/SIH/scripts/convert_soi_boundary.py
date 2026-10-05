#!/usr/bin/env python3
"""Convert the official Survey of India outline shapefile to simplified WGS84 GeoJSON.

The source uses the documented LCC_WGS84 projection and contains one polygon record.
Only the boundary lines are retained because NWIS uses the dataset as a national-outline
overlay, not as an administrative-area or analytical dataset.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path


A = 6_378_137.0
F = 1 / 298.257223563
E = math.sqrt(F * (2 - F))
FALSE_EASTING = 4_000_000.0
FALSE_NORTHING = 4_000_000.0
LON_0 = math.radians(80.0)
LAT_0 = math.radians(24.0)
LAT_1 = math.radians(12.472944)
LAT_2 = math.radians(35.172806)


def _m(latitude: float) -> float:
    return math.cos(latitude) / math.sqrt(1 - E * E * math.sin(latitude) ** 2)


def _t(latitude: float) -> float:
    ratio = (1 - E * math.sin(latitude)) / (1 + E * math.sin(latitude))
    return math.tan(math.pi / 4 - latitude / 2) / ratio ** (E / 2)


N = math.log(_m(LAT_1) / _m(LAT_2)) / math.log(_t(LAT_1) / _t(LAT_2))
BIG_F = _m(LAT_1) / (N * _t(LAT_1) ** N)
RHO_0 = A * BIG_F * _t(LAT_0) ** N


def inverse_lcc(easting: float, northing: float) -> tuple[float, float]:
    x = easting - FALSE_EASTING
    y = RHO_0 - (northing - FALSE_NORTHING)
    rho = math.copysign(math.hypot(x, y), N)
    theta = math.atan2(x, y)
    t_value = (rho / (A * BIG_F)) ** (1 / N)
    latitude = math.pi / 2 - 2 * math.atan(t_value)
    for _ in range(8):
        ratio = (1 - E * math.sin(latitude)) / (1 + E * math.sin(latitude))
        latitude = math.pi / 2 - 2 * math.atan(t_value * ratio ** (E / 2))
    longitude = LON_0 + theta / N
    return math.degrees(longitude), math.degrees(latitude)


def _point_line_distance(point, start, end) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if dx == 0 and dy == 0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    factor = max(
        0.0,
        min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / (dx * dx + dy * dy)),
    )
    return math.hypot(point[0] - (start[0] + factor * dx), point[1] - (start[1] + factor * dy))


def simplify(points: list[tuple[float, float]], tolerance_m: float) -> list[tuple[float, float]]:
    if len(points) <= 3:
        return points
    radial = [points[0]]
    threshold = (tolerance_m * 0.5) ** 2
    for point in points[1:-1]:
        previous = radial[-1]
        if (point[0] - previous[0]) ** 2 + (point[1] - previous[1]) ** 2 >= threshold:
            radial.append(point)
    radial.append(points[-1])
    keep = {0, len(radial) - 1}
    stack = [(0, len(radial) - 1)]
    while stack:
        start_index, end_index = stack.pop()
        distance, split_index = max(
            (
                _point_line_distance(radial[index], radial[start_index], radial[end_index]),
                index,
            )
            for index in range(start_index + 1, end_index)
        ) if end_index - start_index > 1 else (0.0, start_index)
        if distance > tolerance_m:
            keep.add(split_index)
            stack.extend(((start_index, split_index), (split_index, end_index)))
    return [point for index, point in enumerate(radial) if index in keep]


def read_parts(path: Path) -> list[list[tuple[float, float]]]:
    payload = path.read_bytes()
    offset = 100
    all_parts: list[list[tuple[float, float]]] = []
    while offset < len(payload):
        _, content_words = struct.unpack_from(">2i", payload, offset)
        offset += 8
        content_end = offset + content_words * 2
        shape_type = struct.unpack_from("<i", payload, offset)[0]
        if shape_type == 0:
            offset = content_end
            continue
        if shape_type != 5:
            raise ValueError(f"Expected polygon shapefile, found shape type {shape_type}")
        number_of_parts, number_of_points = struct.unpack_from("<2i", payload, offset + 36)
        part_indexes = list(
            struct.unpack_from(f"<{number_of_parts}i", payload, offset + 44)
        )
        point_offset = offset + 44 + number_of_parts * 4
        points = [
            struct.unpack_from("<2d", payload, point_offset + index * 16)
            for index in range(number_of_points)
        ]
        ends = part_indexes[1:] + [number_of_points]
        all_parts.extend(points[start:end] for start, end in zip(part_indexes, ends))
        offset = content_end
    return all_parts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--tolerance-m", type=float, default=1_500.0)
    arguments = parser.parse_args()

    projected_parts = read_parts(arguments.source)
    simplified_parts = [
        simplify(part, arguments.tolerance_m)
        for part in projected_parts
        if len(part) >= 2
    ]
    coordinates = [
        [[round(longitude, 5), round(latitude, 5)] for longitude, latitude in map(lambda point: inverse_lcc(*point), part)]
        for part in simplified_parts
    ]
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Official Boundary of India",
                    "source": "Survey of India",
                    "scale": "1:16M generalized digital data",
                },
                "geometry": {"type": "MultiLineString", "coordinates": coordinates},
            }
        ],
    }
    arguments.destination.parent.mkdir(parents=True, exist_ok=True)
    arguments.destination.write_text(
        json.dumps(geojson, separators=(",", ":")), encoding="utf-8"
    )
    print(
        f"Converted {sum(map(len, projected_parts))} points to "
        f"{sum(map(len, simplified_parts))} points across {len(simplified_parts)} parts"
    )


if __name__ == "__main__":
    main()
