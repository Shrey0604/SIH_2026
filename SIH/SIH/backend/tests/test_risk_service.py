import unittest
from dataclasses import replace
from pathlib import Path

from app.db import initialize_database
from app.services.risk_service import (
    RiskService,
    evidence_score,
    evidence_state,
    kick_telemetry_score,
    mud_loss_telemetry_score,
    stuck_pipe_telemetry_score,
)
from app.services.telemetry_service import TelemetryReplayService
from tests.helpers import sqlite_settings, temporary_directory


class TelemetryScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        replay = TelemetryReplayService(
            Path(__file__).resolve().parents[2] / "demo_data" / "telemetry_scenario.csv"
        )
        self.baseline = replay.sample_at(0)

    def test_mud_loss_score_rises_for_loss_signals(self) -> None:
        baseline_score, _ = mud_loss_telemetry_score(self.baseline, [self.baseline])
        loss_sample = replace(
            self.baseline, flow_out_lpm=1170, pit_volume_m3=81.8, spp_bar=159
        )
        history = [
            replace(self.baseline, seq=index, pit_volume_m3=82 - index * 0.03)
            for index in range(8)
        ]
        loss_score, signals = mud_loss_telemetry_score(loss_sample, history)
        self.assertLess(baseline_score, 0.05)
        self.assertGreater(loss_score, 0.7)
        self.assertGreater(signals["flow_loss_lpm"], 30)

    def test_kick_score_rises_for_influx_signals(self) -> None:
        kick_sample = replace(
            self.baseline, flow_out_lpm=1245, pit_volume_m3=82.3, gas_units=35
        )
        history = [
            replace(self.baseline, seq=index, pit_volume_m3=82 + index * 0.03)
            for index in range(8)
        ]
        score, signals = kick_telemetry_score(kick_sample, history)
        self.assertGreater(score, 0.7)
        self.assertGreater(signals["reverse_flow_lpm"], 30)

    def test_stuck_pipe_score_rises_for_torque_and_rop_signals(self) -> None:
        stuck_sample = replace(self.baseline, torque_knm=20, rop_mph=6, spp_bar=180)
        history = [self.baseline for _ in range(10)]
        score, signals = stuck_pipe_telemetry_score(stuck_sample, history)
        self.assertGreater(score, 0.75)
        self.assertGreater(signals["torque_deviation_knm"], 6)

    def test_evidence_score_and_no_evidence_guard(self) -> None:
        score, breakdown = evidence_score([0.8, 0.7, 0.9], 3, 0.5)
        self.assertAlmostEqual(score, 0.79)
        self.assertEqual(breakdown["recurrence_score"], 1)
        empty_score, empty = evidence_score([], 0, 1)
        self.assertEqual(empty_score, 0)
        self.assertEqual(empty["analog_support"], 0)

    def test_state_thresholds_and_live_corroboration_gate(self) -> None:
        self.assertEqual(evidence_state(0.9, 3, 1, 0.45, 0.65, False), "CLEAR")
        self.assertEqual(evidence_state(0.6, 3, 0, 0.45, 0.65, True), "WATCH")
        self.assertEqual(evidence_state(0.8, 3, 0.1, 0.45, 0.65, True), "WATCH")
        self.assertEqual(evidence_state(0.8, 3, 0.3, 0.45, 0.65, True), "WATCH")
        self.assertEqual(evidence_state(0.8, 3, 0.6, 0.45, 0.65, True), "ELEVATED")


class SeededRiskScenarioTests(unittest.TestCase):
    def test_seeded_scenario_projects_same_formation_and_transitions(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            settings = sqlite_settings(root / "nwis.db", root / "storage")
            repository = initialize_database(settings)
            replay = TelemetryReplayService(settings.telemetry_fixture_path)
            risk = RiskService(
                lookahead_window_m=150,
                watch_threshold=0.45,
                elevated_threshold=0.65,
            )
            wells = repository.list_wells()
            active = next(well for well in wells if well["is_active"])
            intervals = repository.list_formation_intervals()
            events = repository.list_events()

            states = []
            first_watch = None
            first_elevated = None
            for sequence in range(replay.sample_count):
                sample = replay.sample_at(sequence)
                result = risk.evaluate(
                    sample=sample,
                    history=replay.history_through(sequence),
                    active_well=active,
                    wells=wells,
                    intervals=intervals,
                    events=events,
                    selected_radius_km=5,
                    replay_status="running",
                )
                states.append(result["state"])
                if result["state"] == "WATCH" and first_watch is None:
                    first_watch = (sequence, sample.md_m)
                if result["state"] == "ELEVATED" and first_elevated is None:
                    first_elevated = (sequence, sample.md_m)
                for projected in result["projected_events"]:
                    self.assertEqual(projected["formation_name"], "Barail")

            self.assertIsNotNone(first_watch)
            self.assertIsNotNone(first_elevated)
            self.assertEqual(first_watch, (10, 3225.5))
            self.assertEqual(first_elevated, (40, 3287.0))
            self.assertIn("WATCH", states)
            self.assertIn("ELEVATED", states)


if __name__ == "__main__":
    unittest.main()
