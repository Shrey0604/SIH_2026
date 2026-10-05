from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from threading import RLock
from typing import Any


class ReplayStatus(StrEnum):
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class TelemetrySample:
    seq: int
    timestamp_offset_s: int
    md_m: float
    tvd_m: float | None
    rop_mph: float
    wob_kn: float
    rpm: float
    torque_knm: float
    spp_bar: float
    flow_in_lpm: float
    flow_out_lpm: float
    pit_volume_m3: float
    mud_weight_sg: float
    gas_units: float


class TelemetryReplayService:
    def __init__(self, fixture_path: Path):
        self._samples = self._load(fixture_path)
        if not self._samples or self._samples[0].seq != 0:
            raise ValueError("Telemetry fixture must contain sequence zero")
        expected = list(range(len(self._samples)))
        actual = [sample.seq for sample in self._samples]
        if actual != expected:
            raise ValueError("Telemetry fixture sequence must be contiguous")
        self._lock = RLock()
        self._index = 0
        self._status = ReplayStatus.READY

    @staticmethod
    def _load(fixture_path: Path) -> tuple[TelemetrySample, ...]:
        with fixture_path.open(newline="", encoding="utf-8") as handle:
            rows = csv.DictReader(handle)
            return tuple(
                TelemetrySample(
                    seq=int(row["seq"]),
                    timestamp_offset_s=int(row["timestamp_offset_s"]),
                    md_m=float(row["md_m"]),
                    tvd_m=float(row["tvd_m"]) if row["tvd_m"] else None,
                    rop_mph=float(row["rop_mph"]),
                    wob_kn=float(row["wob_kn"]),
                    rpm=float(row["rpm"]),
                    torque_knm=float(row["torque_knm"]),
                    spp_bar=float(row["spp_bar"]),
                    flow_in_lpm=float(row["flow_in_lpm"]),
                    flow_out_lpm=float(row["flow_out_lpm"]),
                    pit_volume_m3=float(row["pit_volume_m3"]),
                    mud_weight_sg=float(row["mud_weight_sg"]),
                    gas_units=float(row["gas_units"]),
                )
                for row in rows
            )

    @property
    def sample_count(self) -> int:
        return len(self._samples)

    def current_sample(self) -> TelemetrySample:
        with self._lock:
            return self._samples[min(self._index, len(self._samples) - 1)]

    def sample_at(self, sequence: int) -> TelemetrySample:
        with self._lock:
            index = max(0, min(sequence, len(self._samples) - 1))
            return self._samples[index]

    def history_through(self, sequence: int, window: int = 12) -> list[TelemetrySample]:
        with self._lock:
            index = max(0, min(sequence, len(self._samples) - 1))
            start = max(0, index - window + 1)
            return list(self._samples[start : index + 1])

    def start(self) -> TelemetrySample:
        with self._lock:
            self._index = 0
            self._status = ReplayStatus.RUNNING
            return self._samples[0]

    def pause(self) -> TelemetrySample:
        with self._lock:
            if self._status == ReplayStatus.RUNNING:
                self._status = ReplayStatus.PAUSED
            return self.current_sample()

    def resume(self) -> TelemetrySample:
        with self._lock:
            if self._status == ReplayStatus.PAUSED:
                self._status = ReplayStatus.RUNNING
            return self.current_sample()

    def reset(self) -> TelemetrySample:
        with self._lock:
            self._index = 0
            self._status = ReplayStatus.READY
            return self._samples[0]

    def next_sample(self) -> TelemetrySample:
        with self._lock:
            sample = self.current_sample()
            if self._status != ReplayStatus.RUNNING:
                return sample
            if self._index >= len(self._samples) - 1:
                self._status = ReplayStatus.COMPLETE
                return sample
            self._index += 1
            return sample

    def advance(self) -> TelemetrySample:
        with self._lock:
            if self._status != ReplayStatus.RUNNING:
                return self.current_sample()
            if self._index >= len(self._samples) - 1:
                self._status = ReplayStatus.COMPLETE
                return self.current_sample()
            self._index += 1
            return self.current_sample()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "status": self._status.value,
                "sequence": self.current_sample().seq,
                "sample": asdict(self.current_sample()),
                "sample_count": len(self._samples),
            }
