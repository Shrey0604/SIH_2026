import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from app.db import initialize_runtime_data
from app.repositories.sqlite import SQLiteRepository
from tests.helpers import sqlite_settings, temporary_directory


class DataFallbackTests(unittest.TestCase):
    def test_demo_supabase_failure_uses_visible_local_fallback(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            base = sqlite_settings(root / "nwis.db", root / "storage")
            settings = replace(
                base,
                data_backend="supabase",
                database_url="postgresql+psycopg://unavailable.invalid/nwis",
            )

            def repository_for(candidate):
                if candidate.data_backend == "supabase":
                    raise ConnectionError("forced Supabase outage")
                return SQLiteRepository(candidate.database_url)

            with patch("app.db.create_repository", side_effect=repository_for):
                repository, storage, effective, reason = initialize_runtime_data(settings)

            self.assertTrue(repository.health_check())
            self.assertEqual(effective.data_backend, "sqlite")
            self.assertIn("Supabase", reason or "")
            self.assertTrue(storage.root.exists())


if __name__ == "__main__":
    unittest.main()
