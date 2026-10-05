import unittest

from app.config import ROOT_DIR
from app.services.telemetry_service import ReplayStatus, TelemetryReplayService


class TelemetryReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.replay = TelemetryReplayService(
            ROOT_DIR / "demo_data" / "telemetry_scenario.csv"
        )

    def test_fixture_is_contiguous_and_starts_at_zero(self) -> None:
        self.assertEqual(self.replay.sample_count, 140)
        self.assertEqual(self.replay.current_sample().seq, 0)
        self.assertEqual(self.replay.snapshot()["status"], ReplayStatus.READY.value)

    def test_controls_are_deterministic(self) -> None:
        first = self.replay.start()
        self.assertEqual(first.seq, 0)
        emitted = self.replay.next_sample()
        self.assertEqual(emitted.seq, 0)
        self.assertEqual(self.replay.current_sample().seq, 1)

        paused = self.replay.pause()
        self.assertEqual(paused.seq, 1)
        self.assertEqual(self.replay.next_sample().seq, 1)
        self.replay.resume()
        self.assertEqual(self.replay.next_sample().seq, 1)

        reset_sample = self.replay.reset()
        self.assertEqual(reset_sample, first)
        self.assertEqual(self.replay.snapshot()["sequence"], 0)
        self.assertEqual(self.replay.snapshot()["status"], ReplayStatus.READY.value)


if __name__ == "__main__":
    unittest.main()

