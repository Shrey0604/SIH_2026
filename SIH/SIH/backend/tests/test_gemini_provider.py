from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from google.genai.errors import ServerError

from app.ai import (
    GeminiAIProvider,
    GroundedAnswer,
    ProviderResponseError,
    ProviderUnavailableError,
)
from tests.helpers import sqlite_settings


class FakeModels:
    def __init__(self):
        self.responses: list[object] = []
        self.embedding_vectors: list[list[float]] = []
        self.generate_calls: list[dict[str, object]] = []
        self.embed_calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs):
        self.generate_calls.append(kwargs)
        if not self.responses:
            raise AssertionError("No fake Gemini response was queued")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response

    def embed_content(self, **kwargs):
        self.embed_calls.append(kwargs)
        return SimpleNamespace(
            embeddings=[SimpleNamespace(values=vector) for vector in self.embedding_vectors]
        )


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


class GeminiProviderTests(unittest.TestCase):
    def _settings(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        return replace(
            sqlite_settings(root / "nwis.db", root / "storage"),
            gemini_api_key="configured-for-test",
        )

    def tearDown(self) -> None:
        temporary = getattr(self, "temporary", None)
        if temporary is not None:
            temporary.cleanup()

    def test_initialization_requires_key_without_injected_client(self) -> None:
        settings = replace(self._settings(), gemini_api_key=None)
        with self.assertRaisesRegex(ProviderUnavailableError, "GEMINI_API_KEY"):
            GeminiAIProvider(settings)

        provider = GeminiAIProvider(settings, client=FakeClient())
        self.assertEqual(provider.extraction_model, "test-extraction")
        self.assertEqual(provider.embedding_dimension, 3)

    def test_structured_extraction_parses_strict_json(self) -> None:
        client = FakeClient()
        client.models.responses.append(
            SimpleNamespace(
                parsed=None,
                text=json.dumps(
                    {
                        "events": [
                            {
                                "hazard_type": "MUD_LOSS",
                                "formation": "Barail",
                                "start_md_m": 3210,
                                "end_md_m": 3218,
                                "severity": "MEDIUM",
                                "description": "Partial circulation loss was observed in Barail.",
                                "historical_response": "Flow was reduced and monitored.",
                                "page_number": 2,
                                "evidence_text": "Partial circulation loss was observed in Barail.",
                                "confidence": 0.93,
                            }
                        ]
                    }
                ),
            )
        )
        provider = GeminiAIProvider(self._settings(), client=client)
        result = provider.extract_events([{"page_number": 2, "text": "source"}])
        self.assertEqual(result.events[0].hazard_type, "MUD_LOSS")
        self.assertEqual(result.events[0].page_number, 2)
        config = client.models.generate_calls[0]["config"]
        self.assertEqual(config.response_mime_type, "application/json")
        wire_schema = config.response_schema
        self.assertNotIn("additionalProperties", json.dumps(wire_schema))
        self.assertNotIn("$ref", json.dumps(wire_schema))
        self.assertNotIn("$defs", wire_schema)
        self.assertNotIn("minLength", json.dumps(wire_schema))
        event_schema = wire_schema["properties"]["events"]["items"]
        self.assertTrue(event_schema["properties"]["formation"]["nullable"])

    def test_malformed_structured_output_is_rejected(self) -> None:
        client = FakeClient()
        client.models.responses.append(SimpleNamespace(parsed=None, text="not-json"))
        provider = GeminiAIProvider(self._settings(), client=client)
        with self.assertRaises(ProviderResponseError):
            provider.extract_events([{"page_number": 1, "text": "source"}])

    @patch("app.ai.provider.time.sleep")
    def test_transient_gemini_failure_is_retried(self, sleep) -> None:
        client = FakeClient()
        client.models.responses.extend(
            [
                ServerError(503, {"error": {"message": "temporary demand"}}),
                SimpleNamespace(parsed=None, text='{"events": []}'),
            ]
        )
        provider = GeminiAIProvider(self._settings(), client=client)
        result = provider.extract_events([{"page_number": 1, "text": "source"}])
        self.assertEqual(result.events, [])
        self.assertEqual(len(client.models.generate_calls), 2)
        sleep.assert_called_once_with(1)

    def test_scanned_page_recovery_uses_inline_png(self) -> None:
        client = FakeClient()
        client.models.responses.append(SimpleNamespace(text="Recovered page text"))
        provider = GeminiAIProvider(self._settings(), client=client)
        recovered = provider.recover_scanned_page(b"\x89PNG\r\n\x1a\nbytes", page_number=4)
        self.assertEqual(recovered, "Recovered page text")
        contents = client.models.generate_calls[0]["contents"]
        self.assertEqual(contents[0].inline_data.mime_type, "image/png")

    def test_embedding_generation_enforces_configured_dimension(self) -> None:
        client = FakeClient()
        client.models.embedding_vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        provider = GeminiAIProvider(self._settings(), client=client)
        vectors = provider.generate_embedding(
            ["document one", "document two"], task_type="RETRIEVAL_DOCUMENT"
        )
        self.assertEqual([len(vector) for vector in vectors], [3, 3])
        config = client.models.embed_calls[0]["config"]
        self.assertEqual(config.task_type, "RETRIEVAL_DOCUMENT")
        self.assertEqual(config.output_dimensionality, 3)

        client.models.embedding_vectors = [[0.1, 0.2]]
        with self.assertRaisesRegex(ProviderResponseError, "dimension"):
            provider.generate_embedding(["bad"], task_type="RETRIEVAL_QUERY")

    def test_grounded_answer_preserves_only_supplied_sources(self) -> None:
        client = FakeClient()
        client.models.responses.append(
            SimpleNamespace(
                parsed=GroundedAnswer(
                    answer_markdown=(
                        "Mud loss was recorded. Historical response observed: flow was reduced [SRC-1]."
                    ),
                    source_ids=["SRC-1"],
                    insufficient_evidence=False,
                )
            )
        )
        provider = GeminiAIProvider(self._settings(), client=client)
        answer = provider.generate_answer(
            question="What happened?",
            live_context={"formation": "Barail"},
            evidence_bundle=[{"source_id": "SRC-1", "text": "Mud loss."}],
        )
        self.assertEqual(answer.source_ids, ["SRC-1"])

        client.models.responses.append(
            SimpleNamespace(
                parsed=GroundedAnswer(
                    answer_markdown="Unsupported [MADE-UP].",
                    source_ids=["MADE-UP"],
                    insufficient_evidence=False,
                )
            )
        )
        with self.assertRaisesRegex(ProviderResponseError, "invented citation"):
            provider.generate_answer(
                question="What happened?",
                live_context={},
                evidence_bundle=[{"source_id": "SRC-1", "text": "Mud loss."}],
            )

        client.models.responses.append(
            SimpleNamespace(
                parsed=GroundedAnswer(
                    answer_markdown="Mud loss was recorded without an inline reference.",
                    source_ids=["SRC-1"],
                    insufficient_evidence=False,
                )
            )
        )
        with self.assertRaisesRegex(ProviderResponseError, "inline citations"):
            provider.generate_answer(
                question="What happened?",
                live_context={},
                evidence_bundle=[{"source_id": "SRC-1", "text": "Mud loss."}],
            )


if __name__ == "__main__":
    unittest.main()
