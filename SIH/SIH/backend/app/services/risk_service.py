from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from typing import Any, Iterable

from app.services.analog_service import (
    analog_relevance_score,
    evidence_quality_score,
    haversine_distance_km,
    lookahead_proximity_score,
    project_event_depth,
    spatial_score,
)
from app.services.formation_service import clamp01, find_formation_at_depth
from app.services.telemetry_service import TelemetrySample


def _linear_slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    count = len(values)
    x_mean = (count - 1) / 2
    y_mean = sum(values) / count
    numerator = sum((index - x_mean) * (value - y_mean) for index, value in enumerate(values))
    denominator = sum((index - x_mean) ** 2 for index in range(count))
    return numerator / denominator if denominator else 0.0


def mud_loss_telemetry_score(
    sample: TelemetrySample, history: Iterable[TelemetrySample]
) -> tuple[float, dict[str, float]]:
    recent = list(history)[-8:]
    flow_loss_lpm = max(0.0, sample.flow_in_lpm - sample.flow_out_lpm)
    flow_score = clamp01((flow_loss_lpm - 2.0) / 18.0)
    pit_slope = _linear_slope([item.pit_volume_m3 for item in recent])
    pit_score = clamp01((-pit_slope - 0.001) / 0.009)
    pressure_drop_bar = max(0.0, 166.0 - sample.spp_bar)
    pressure_score = clamp01(pressure_drop_bar / 6.0)
    score = clamp01(0.50 * flow_score + 0.35 * pit_score + 0.15 * pressure_score)
    return score, {
        "flow_loss_lpm": round(flow_loss_lpm, 3),
        "flow_imbalance_score": round(flow_score, 4),
        "pit_slope_m3_per_sample": round(pit_slope, 5),
        "pit_decline_score": round(pit_score, 4),
        "pressure_drop_bar": round(pressure_drop_bar, 3),
        "pressure_score": round(pressure_score, 4),
    }


def kick_telemetry_score(
    sample: TelemetrySample, history: Iterable[TelemetrySample]
) -> tuple[float, dict[str, float]]:
    recent = list(history)[-8:]
    reverse_flow_lpm = max(0.0, sample.flow_out_lpm - sample.flow_in_lpm)
    flow_score = clamp01((reverse_flow_lpm - 2.0) / 18.0)
    pit_slope = _linear_slope([item.pit_volume_m3 for item in recent])
    pit_score = clamp01((pit_slope - 0.001) / 0.009)
    baseline_gas = sum(item.gas_units for item in recent[:3]) / max(1, len(recent[:3]))
    gas_score = clamp01((sample.gas_units - baseline_gas - 1.0) / 8.0)
    score = clamp01(0.45 * flow_score + 0.35 * pit_score + 0.20 * gas_score)
    return score, {
        "reverse_flow_lpm": round(reverse_flow_lpm, 3),
        "reverse_flow_score": round(flow_score, 4),
        "pit_slope_m3_per_sample": round(pit_slope, 5),
        "pit_rise_score": round(pit_score, 4),
        "gas_rise_score": round(gas_score, 4),
    }


def stuck_pipe_telemetry_score(
    sample: TelemetrySample, history: Iterable[TelemetrySample]
) -> tuple[float, dict[str, float]]:
    recent = list(history)[-12:]
    baseline_torque = sum(item.torque_knm for item in recent) / max(1, len(recent))
    baseline_rop = sum(item.rop_mph for item in recent) / max(1, len(recent))
    torque_score = clamp01((sample.torque_knm - baseline_torque) / 4.0)
    rop_ratio = sample.rop_mph / baseline_rop if baseline_rop else 1.0
    rop_drop_score = clamp01((0.85 - rop_ratio) / 0.35)
    pressure_score = clamp01(abs(sample.spp_bar - 166.0) / 15.0)
    score = clamp01(0.50 * torque_score + 0.35 * rop_drop_score + 0.15 * pressure_score)
    return score, {
        "torque_deviation_knm": round(sample.torque_knm - baseline_torque, 3),
        "torque_score": round(torque_score, 4),
        "rop_ratio": round(rop_ratio, 4),
        "rop_drop_score": round(rop_drop_score, 4),
        "pressure_score": round(pressure_score, 4),
    }


def evidence_score(
    analog_scores: list[float], distinct_supporting_wells: int, telemetry_score: float
) -> tuple[float, dict[str, float]]:
    if not analog_scores:
        return 0.0, {
            "analog_support": 0.0,
            "recurrence_score": 0.0,
            "telemetry_score": round(clamp01(telemetry_score), 4),
        }
    top_scores = sorted((clamp01(score) for score in analog_scores), reverse=True)[:3]
    analog_support = sum(top_scores) / len(top_scores)
    recurrence = clamp01(distinct_supporting_wells / 3.0)
    live_score = clamp01(telemetry_score)
    score = clamp01(0.55 * analog_support + 0.25 * recurrence + 0.20 * live_score)
    return score, {
        "analog_support": round(analog_support, 4),
        "recurrence_score": round(recurrence, 4),
        "telemetry_score": round(live_score, 4),
    }


def evidence_state(
    score: float,
    supporting_wells: int,
    telemetry_score: float,
    watch_threshold: float,
    elevated_threshold: float,
    has_evidence: bool,
    live_corroboration_threshold: float = 0.50,
) -> str:
    if not has_evidence or supporting_wells < 2 or score < watch_threshold:
        return "CLEAR"
    if (
        score >= elevated_threshold
        and telemetry_score >= live_corroboration_threshold
    ):
        return "ELEVATED"
    return "WATCH"


class RiskService:
    def __init__(
        self,
        *,
        lookahead_window_m: float,
        watch_threshold: float,
        elevated_threshold: float,
        live_corroboration_threshold: float = 0.50,
    ):
        self.lookahead_window_m = lookahead_window_m
        self.watch_threshold = watch_threshold
        self.elevated_threshold = elevated_threshold
        self.live_corroboration_threshold = live_corroboration_threshold

    def evaluate(
        self,
        *,
        sample: TelemetrySample,
        history: list[TelemetrySample],
        active_well: dict[str, Any],
        wells: list[dict[str, Any]],
        intervals: list[dict[str, Any]],
        events: list[dict[str, Any]],
        selected_radius_km: float,
        replay_status: str,
    ) -> dict[str, Any]:
        active_intervals = [
            interval for interval in intervals if interval["well_id"] == active_well["id"]
        ]
        current_formation = find_formation_at_depth(active_intervals, sample.md_m)
        if current_formation is None:
            return self._empty_result(sample, active_intervals, replay_status)

        interval_by_key = {
            (interval["well_id"], interval["formation_id"]): interval
            for interval in intervals
        }
        wells_by_id = {well["id"]: well for well in wells}
        candidates: list[dict[str, Any]] = []
        for event in events:
            if event["formation_id"] != current_formation["formation_id"]:
                continue
            offset_well = wells_by_id[event["well_id"]]
            if offset_well["id"] == active_well["id"]:
                continue
            if offset_well.get("well_scope") != "LOCAL_OFFSET":
                continue
            distance_km = haversine_distance_km(
                active_well["latitude"],
                active_well["longitude"],
                offset_well["latitude"],
                offset_well["longitude"],
            )
            if distance_km > selected_radius_km:
                continue
            offset_interval = interval_by_key.get(
                (event["well_id"], event["formation_id"])
            )
            if offset_interval is None:
                continue
            relative_position, projected_md_m = project_event_depth(
                event["start_md_m"],
                event["end_md_m"],
                offset_interval["top_md_m"],
                offset_interval["base_md_m"],
                current_formation["top_md_m"],
                current_formation["base_md_m"],
            )
            lookahead_m = projected_md_m - sample.md_m
            if not 0 < lookahead_m <= self.lookahead_window_m:
                continue
            spatial = spatial_score(distance_km, selected_radius_km)
            proximity = lookahead_proximity_score(
                lookahead_m, self.lookahead_window_m
            )
            quality = evidence_quality_score(
                event["extraction_confidence"], event["has_exact_page_evidence"]
            )
            relevance = analog_relevance_score(True, spatial, proximity, quality)
            candidates.append(
                {
                    **event,
                    "well_name": offset_well["name"],
                    "distance_km": round(distance_km, 3),
                    "relative_position": round(relative_position, 5),
                    "projected_md_m": round(projected_md_m, 3),
                    "lookahead_m": round(lookahead_m, 3),
                    "analog_relevance": round(relevance, 4),
                    "score_breakdown": {
                        "formation_match": 1.0,
                        "spatial_score": round(spatial, 4),
                        "lookahead_proximity_score": round(proximity, 4),
                        "evidence_quality": round(quality, 4),
                    },
                }
            )

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for candidate in candidates:
            grouped[candidate["hazard_type"]].append(candidate)

        telemetry_functions = {
            "MUD_LOSS": mud_loss_telemetry_score,
            "KICK": kick_telemetry_score,
            "STUCK_PIPE": stuck_pipe_telemetry_score,
        }
        hazards: list[dict[str, Any]] = []
        for hazard_type, analogs in grouped.items():
            live_score, live_signals = telemetry_functions[hazard_type](sample, history)
            top_analogs = sorted(
                analogs, key=lambda item: item["analog_relevance"], reverse=True
            )[:3]
            supporting_wells = len({item["well_id"] for item in top_analogs})
            score, breakdown = evidence_score(
                [item["analog_relevance"] for item in top_analogs],
                supporting_wells,
                live_score,
            )
            state = evidence_state(
                score,
                supporting_wells,
                live_score,
                self.watch_threshold,
                self.elevated_threshold,
                has_evidence=all(item["has_exact_page_evidence"] for item in top_analogs),
                live_corroboration_threshold=self.live_corroboration_threshold,
            )
            if replay_status == "ready":
                state = "CLEAR"
            weighted_total = sum(item["analog_relevance"] for item in top_analogs)
            projected_md_m = (
                sum(
                    item["projected_md_m"] * item["analog_relevance"]
                    for item in top_analogs
                )
                / weighted_total
            )
            hazards.append(
                {
                    "hazard_type": hazard_type,
                    "state": state,
                    "evidence_score": round(score * 100, 1),
                    "projected_hazard_md_m": round(projected_md_m, 1),
                    "lookahead_m": round(projected_md_m - sample.md_m, 1),
                    "supporting_wells": supporting_wells,
                    "score_breakdown": breakdown,
                    "live_signals": live_signals,
                    "analogs": top_analogs,
                }
            )

        priority = {"ELEVATED": 2, "WATCH": 1, "CLEAR": 0}
        hazards.sort(
            key=lambda item: (priority[item["state"]], item["evidence_score"]),
            reverse=True,
        )
        overall_state = hazards[0]["state"] if hazards else "CLEAR"
        return {
            "state": overall_state,
            "current_formation": current_formation,
            "formations": active_intervals,
            "lookahead_window_m": self.lookahead_window_m,
            "projected_events": sorted(
                candidates, key=lambda item: item["projected_md_m"]
            ),
            "active_hazard": hazards[0] if hazards else None,
            "hazards": hazards,
            "sample": asdict(sample),
        }

    def _empty_result(
        self,
        sample: TelemetrySample,
        intervals: list[dict[str, Any]],
        replay_status: str,
    ) -> dict[str, Any]:
        del replay_status
        return {
            "state": "CLEAR",
            "current_formation": None,
            "formations": intervals,
            "lookahead_window_m": self.lookahead_window_m,
            "projected_events": [],
            "active_hazard": None,
            "hazards": [],
            "sample": asdict(sample),
        }
