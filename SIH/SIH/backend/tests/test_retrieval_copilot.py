from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.ai import GroundedAnswer, ProviderUnavailableError
from app.db import initialize_database
from app.services.copilot_service import CopilotService
from app.services.retrieval_service import RetrievalService
from tests.helpers import sqlite_settings


SCRIPTED_QUESTION = "What happened in nearby wells in the Barail interval ahead of us?"
SELECTED_WELLS = ["off-01", "off-02", "off-03"]


class FakeEmbeddings:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.queries: list[str] = []

    def search(self, repository, query: str, *, top_k: int = 6):
        del repository, top_k
        self.queries.append(query)
        if self.fail:
            raise ProviderUnavailableError("embedding provider unavailable")
        return [
            {
                "document_id": "document-off-03-ddr-excerpt-pdf",
                "page_number": 2,
                "similarity": 0.91,
            }
        ]


class CitingProvider:
    def generate_answer(self, *, question, live_context, evidence_bundle):
        del question, live_context
        first, second = evidence_bundle[:2]
        return GroundedAnswer(
            answer_markdown=(
                f"Recurring mud loss was recorded [{first['source_id']}] "
                f"and [{second['source_id']}]. Historical response observed: flow was reduced."
            ),
            source_ids=[first["source_id"], second["source_id"]],
            insufficient_evidence=False,
        )


class FailingProvider:
    def generate_answer(self, **kwargs):
        del kwargs
        raise ProviderUnavailableError("Gemini unavailable")


class RetrievalCopilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.repository = initialize_database(
            sqlite_settings(root / "nwis.db", root / "storage")
        )

    def tearDown(self) -> None:
        engine = getattr(self.repository, "engine", None)
        if engine is not None:
            engine.dispose()
        self.temporary.cleanup()

    def test_knowledge_search_filters_structured_evidenced_events(self) -> None:
        retrieval = RetrievalService(self.repository, None)
        results = retrieval.search_events(
            query="mud loss", formation="Barail", hazard_type="MUD_LOSS"
        )
        self.assertEqual(len(results), 4)
        self.assertTrue(all(result["evidence"] for result in results))
        self.assertTrue(all(result["formation_name"] == "Barail" for result in results))
        off_three = retrieval.search_events(well_id="off-03")
        self.assertEqual([result["id"] for result in off_three], ["evt-ml-03"])

    def test_scripted_retrieval_uses_embedding_and_metadata_filters(self) -> None:
        embeddings = FakeEmbeddings()
        retrieval = RetrievalService(self.repository, embeddings)
        result = retrieval.retrieve(
            question=SCRIPTED_QUESTION,
            formation="Barail",
            selected_well_ids=SELECTED_WELLS,
        )
        self.assertEqual(embeddings.queries, [SCRIPTED_QUESTION])
        self.assertEqual(len(result["evidence"]), 3)
        self.assertEqual(
            {item["well_id"] for item in result["evidence"]}, set(SELECTED_WELLS)
        )
        self.assertTrue(
            all(item["hazard_type"] == "MUD_LOSS" for item in result["evidence"])
        )

    def test_embedding_failure_preserves_raw_evidence_retrieval(self) -> None:
        retrieval = RetrievalService(self.repository, FakeEmbeddings(fail=True))
        result = retrieval.retrieve(
            question=SCRIPTED_QUESTION,
            formation="Barail",
            selected_well_ids=SELECTED_WELLS,
        )
        self.assertEqual(result["retrieval_mode"], "metadata_lexical")
        self.assertIn("embedding provider unavailable", result["embedding_error"])
        self.assertEqual(len(result["evidence"]), 3)

    def test_known_formation_name_is_a_retrieval_anchor(self) -> None:
        retrieval = RetrievalService(self.repository, None)
        result = retrieval.retrieve(
            question="What is Barail?",
            formation="Barail",
            selected_well_ids=SELECTED_WELLS,
        )
        self.assertEqual(result["matched_formation"], "Barail")
        self.assertEqual(len(result["evidence"]), 4)
        self.assertTrue(
            all(item["formation"] == "Barail" for item in result["evidence"])
        )

    def test_explicit_formation_overrides_live_alert_scope(self) -> None:
        retrieval = RetrievalService(self.repository, None)
        result = retrieval.retrieve(
            question="What is Kopili?",
            formation="Barail",
            selected_well_ids=SELECTED_WELLS,
        )
        self.assertEqual(result["matched_formation"], "Kopili")
        self.assertEqual([item["event_id"] for item in result["evidence"]], ["evt-sp-01"])

    def test_known_well_name_targets_that_wells_evidence(self) -> None:
        retrieval = RetrievalService(self.repository, None)
        result = retrieval.retrieve(
            question="What happened in NWIS-OFF-03?",
            formation="Barail",
            selected_well_ids=SELECTED_WELLS,
        )
        self.assertEqual(result["matched_well_id"], "off-03")
        self.assertEqual([item["event_id"] for item in result["evidence"]], ["evt-ml-03"])

    def test_copilot_returns_cited_answer_and_provider_failure_summary(self) -> None:
        retrieval = RetrievalService(self.repository, None)
        context = {"formation": "Barail", "active_well_name": "NWIS-ACT-01"}
        live = CopilotService(retrieval, CitingProvider()).query(
            question=SCRIPTED_QUESTION,
            live_context=context,
            selected_well_ids=SELECTED_WELLS,
        )
        self.assertEqual(live["generation_mode"], "gemini")
        self.assertGreaterEqual(len(live["sources"]), 2)
        self.assertTrue(
            all(source["source_id"] in live["answer_markdown"] for source in live["sources"])
        )

        fallback = CopilotService(retrieval, FailingProvider()).query(
            question=SCRIPTED_QUESTION,
            live_context=context,
            selected_well_ids=SELECTED_WELLS,
        )
        self.assertEqual(fallback["generation_mode"], "deterministic_evidence_summary")
        self.assertEqual(len(fallback["sources"]), 3)
        self.assertIn("Generated synthesis unavailable", fallback["answer_markdown"])
        self.assertIn("Historical response observed", fallback["answer_markdown"])

        formation_answer = CopilotService(retrieval, FailingProvider()).query(
            question="What is Barail?",
            live_context=context,
            selected_well_ids=SELECTED_WELLS,
        )
        self.assertFalse(formation_answer["insufficient_evidence"])
        self.assertEqual(len(formation_answer["sources"]), 3)

    def test_unsupported_question_is_explicitly_insufficient(self) -> None:
        result = CopilotService(
            RetrievalService(self.repository, None), CitingProvider()
        ).query(
            question="What is the weather tomorrow?",
            live_context={"formation": "Barail"},
            selected_well_ids=SELECTED_WELLS,
        )
        self.assertTrue(result["insufficient_evidence"])
        self.assertEqual(result["sources"], [])
        self.assertIn("page-backed NWIS evidence", result["answer_markdown"])


if __name__ == "__main__":
    unittest.main()
