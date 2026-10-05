import tempfile
import unittest
from pathlib import Path

from app.storage.local import LocalStorageAdapter


class LocalStorageTests(unittest.TestCase):
    def test_round_trip_and_path_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = LocalStorageAdapter(Path(directory))
            path = storage.put("reports/example.pdf", b"pdf", "application/pdf")
            self.assertEqual(path, "reports/example.pdf")
            self.assertEqual(storage.get(path), b"pdf")
            with self.assertRaises(ValueError):
                storage.put("../escape", b"bad", "application/octet-stream")


if __name__ == "__main__":
    unittest.main()
