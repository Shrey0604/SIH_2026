import unittest
from pathlib import Path

from app.container import AppContainer
from app.db import initialize_database
from app.routers.demo import reset_demo
from app.services.telemetry_service import TelemetryReplayService
from app.services.risk_service import RiskService
from app.services.evidence_service import EvidenceService
from app.storage.local import LocalStorageAdapter
from tests.helpers import sqlite_settings, temporary_directory


class DemoResetTests(unittest.TestCase):
    def test_reset_is_idempotent(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            settings = sqlite_settings(root / "nwis.db", root / "storage")
            repository = initialize_database(settings)
            replay = TelemetryReplayService(settings.telemetry_fixture_path)
            storage = LocalStorageAdapter(settings.local_storage_path)
            container = AppContainer(
                settings=settings,
                repository=repository,
                telemetry=replay,
                risk=RiskService(
                    lookahead_window_m=150,
                    watch_threshold=0.45,
                    elevated_threshold=0.65,
                ),
                storage=storage,
                evidence=EvidenceService(repository, storage),
            )
            replay.start()
            replay.next_sample()

            first = reset_demo(container)
            second = reset_demo(container)

            self.assertEqual(first, second)
            self.assertEqual(second.replay.sequence, 0)
            self.assertEqual(second.replay.status, "ready")
            self.assertEqual(second.runtime_alerts, 0)


if __name__ == "__main__":
    unittest.main()
