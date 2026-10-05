import unittest
from pathlib import Path

from app.db import initialize_database
from tests.helpers import sqlite_settings, temporary_directory


class RepositorySeedTests(unittest.TestCase):
    def test_seed_contains_required_wells_events_and_evidence(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            repository = initialize_database(
                sqlite_settings(root / "nwis.db", root / "storage")
            )
            counts = repository.counts()

            self.assertEqual(counts["wells"], 31)
            self.assertEqual(counts["events"], 6)
            self.assertEqual(counts["evidence"], 6)
            snapshot = repository.seed_snapshot()
            active = [well for well in snapshot["wells"] if well[2]]
            self.assertEqual(active, [("active-01", "NWIS-ACT-01", True)])
            wells = repository.list_wells()
            self.assertEqual(
                len([well for well in wells if well["well_scope"] == "CONTEXT"]),
                24,
            )
            self.assertEqual(
                len(
                    [
                        well
                        for well in wells
                        if not well["is_active"]
                        and well["well_scope"] == "LOCAL_OFFSET"
                    ]
                ),
                6,
            )

    def test_reseed_and_fresh_database_are_identical(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            settings_a = sqlite_settings(root / "a.db", root / "storage-a")
            repository_a = initialize_database(settings_a)
            first = repository_a.seed_snapshot()
            repository_a.seed_from_file(settings_a.seed_fixture_path)
            self.assertEqual(repository_a.seed_snapshot(), first)

            settings_b = sqlite_settings(root / "b.db", root / "storage-b")
            repository_b = initialize_database(settings_b)
            self.assertEqual(repository_b.seed_snapshot(), first)


if __name__ == "__main__":
    unittest.main()
