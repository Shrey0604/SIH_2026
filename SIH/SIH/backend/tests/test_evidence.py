import unittest
from pathlib import Path

from app.db import initialize_database
from app.services.evidence_service import EvidenceService
from app.storage.local import LocalStorageAdapter
from tests.helpers import sqlite_settings, temporary_directory


class EvidenceChainTests(unittest.TestCase):
    def test_every_seeded_event_resolves_to_stored_document_page(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            settings = sqlite_settings(root / "nwis.db", root / "storage")
            repository = initialize_database(settings)
            service = EvidenceService(
                repository, LocalStorageAdapter(settings.local_storage_path)
            )

            for summary in repository.list_events():
                event = service.event_with_evidence(summary["id"])
                self.assertIsNotNone(event)
                assert event is not None
                self.assertTrue(event["has_exact_page_evidence"])
                self.assertGreaterEqual(len(event["evidence"]), 1)
                reference = event["evidence"][0]
                image, document = service.render_page_png(
                    reference["document_id"], reference["page_number"]
                )
                self.assertTrue(image.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertEqual(document["filename"], reference["filename"])

    def test_missing_event_has_no_evidence_chain(self) -> None:
        with temporary_directory() as directory:
            root = Path(directory)
            settings = sqlite_settings(root / "nwis.db", root / "storage")
            repository = initialize_database(settings)
            service = EvidenceService(
                repository, LocalStorageAdapter(settings.local_storage_path)
            )
            self.assertIsNone(service.event_with_evidence("missing"))


if __name__ == "__main__":
    unittest.main()
