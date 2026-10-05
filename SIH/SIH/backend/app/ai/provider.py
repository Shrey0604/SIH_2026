from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import ValidationError

from app.ai.schemas import ExtractionResult, GroundedAnswer
from app.config import Settings


T = TypeVar("T")
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class ProviderUnavailableError(RuntimeError):
    """The configured model service could not complete the request."""


class ProviderResponseError(ValueError):
    """The model responded, but the result did not satisfy the strict contract."""


class AIProvider(Protocol):
    provider_name: str
    embedding_model: str
    embedding_dimension: int

    def extract_events(
        self,
        pages: list[dict[str, object]],
        *,
        validation_feedback: str | None = None,
    ) -> ExtractionResult: ...

    def recover_scanned_page(self, image_png: bytes, *, page_number: int) -> str: ...

    def generate_embedding(
        self, texts: list[str], *, task_type: str
    ) -> list[list[float]]: ...

    def generate_answer(
        self,
        *,
        question: str,
        live_context: dict[str, object],
        evidence_bundle: list[dict[str, object]],
    ) -> GroundedAnswer: ...


EXTRACTION_SYSTEM_PROMPT = """You extract drilling operational events from engineering reports.
Return only events explicitly supported by the supplied page text. Never infer an event from absence,
plans, negation, or general background. Never invent depth, formation, or operational response.
The evidence_text must be a verbatim, contiguous excerpt from the cited page and must directly support
the event. Preserve the one-based page number. Valid hazards are MUD_LOSS, STUCK_PIPE, and KICK.
Use measured depth in metres. If there is no supported event, return an empty events list."""


ANSWER_SYSTEM_PROMPT = """You are the NWIS evidence synthesis service. Answer only from the supplied
evidence bundle. Cite every material factual claim using only the supplied source IDs. Distinguish
documented facts from clearly labelled inference. Describe mitigations only as 'Historical response
observed'. Never issue autonomous drilling-control instructions. If the supplied evidence does not
support an answer, say that evidence is insufficient. Never invent or alter a citation ID. When two
or more relevant sources are supplied, cite at least two distinct sources. For a question asking what
a named entity is, give the bounded operational description established by the records and explicitly
say when the corpus does not contain a broader geological or general definition."""


def _gemini_wire_schema(schema: type[ExtractionResult] | type[GroundedAnswer]) -> dict[str, Any]:
    """Keep strict Pydantic validation while sending Gemini's supported JSON-schema subset."""

    source = schema.model_json_schema()
    definitions = source.get("$defs", {})
    supported_keys = {"type", "properties", "required", "items", "enum"}

    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/$defs/"):
                definition = definitions.get(reference.removeprefix("#/$defs/"))
                if definition is None:
                    raise ValueError(f"Unresolved schema reference: {reference}")
                return clean(definition)
            alternatives = value.get("anyOf")
            if isinstance(alternatives, list):
                non_null = [item for item in alternatives if item.get("type") != "null"]
                has_null = any(item.get("type") == "null" for item in alternatives)
                if has_null and len(non_null) == 1:
                    nullable = clean(non_null[0])
                    nullable["nullable"] = True
                    return nullable
            cleaned: dict[str, Any] = {}
            for key, item in value.items():
                if key == "properties" and isinstance(item, dict):
                    cleaned[key] = {
                        property_name: clean(property_schema)
                        for property_name, property_schema in item.items()
                    }
                elif key in supported_keys:
                    cleaned[key] = clean(item)
            return cleaned
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    return clean(source)


class GeminiAIProvider:
    """The only runtime boundary containing Gemini SDK calls."""

    provider_name = "gemini"

    def __init__(self, settings: Settings, *, client: Any | None = None):
        if client is None and not settings.gemini_api_key:
            raise ProviderUnavailableError("GEMINI_API_KEY is not configured")
        self.client = client or genai.Client(api_key=settings.gemini_api_key)
        self.extraction_model = settings.gemini_extraction_model
        self.copilot_model = settings.gemini_copilot_model
        self.embedding_model = settings.gemini_embedding_model
        self.embedding_dimension = settings.gemini_embedding_dim

    @staticmethod
    def _call_with_transient_retry(operation: Callable[[], T]) -> T:
        for attempt in range(3):
            try:
                return operation()
            except APIError as error:
                if error.code not in TRANSIENT_STATUS_CODES or attempt == 2:
                    raise
                time.sleep(2**attempt)
        raise AssertionError("unreachable")

    @staticmethod
    def _parse_structured(
        response: Any, schema: type[ExtractionResult] | type[GroundedAnswer]
    ) -> ExtractionResult | GroundedAnswer:
        parsed = getattr(response, "parsed", None)
        try:
            if isinstance(parsed, schema):
                return parsed
            if parsed is not None:
                return schema.model_validate(parsed)
            text = getattr(response, "text", None)
            if not text:
                raise ValueError("Gemini returned no structured response body")
            return schema.model_validate_json(text)
        except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise ProviderResponseError(
                f"Malformed Gemini structured output: {error}"
            ) from error

    def extract_events(
        self,
        pages: list[dict[str, object]],
        *,
        validation_feedback: str | None = None,
    ) -> ExtractionResult:
        page_blocks = "\n\n".join(
            f"--- PAGE {page['page_number']} ---\n{page['text']}" for page in pages
        )
        retry_note = (
            f"\n\nThe previous result failed deterministic validation: {validation_feedback}. "
            "Correct only those issues; do not invent evidence."
            if validation_feedback
            else ""
        )
        try:
            response = self._call_with_transient_retry(
                lambda: self.client.models.generate_content(
                    model=self.extraction_model,
                    contents=(
                        f"Extract supported events from this report:\n\n{page_blocks}{retry_note}"
                    ),
                    config=types.GenerateContentConfig(
                        system_instruction=EXTRACTION_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                    response_schema=_gemini_wire_schema(ExtractionResult),
                        temperature=0,
                    ),
                )
            )
        except Exception as error:
            raise ProviderUnavailableError(
                f"Gemini structured extraction failed: {error}"
            ) from error
        result = self._parse_structured(response, ExtractionResult)
        assert isinstance(result, ExtractionResult)
        return result

    def recover_scanned_page(self, image_png: bytes, *, page_number: int) -> str:
        try:
            response = self._call_with_transient_retry(
                lambda: self.client.models.generate_content(
                    model=self.extraction_model,
                    contents=[
                        types.Part.from_bytes(data=image_png, mime_type="image/png"),
                        (
                            f"Transcribe page {page_number} faithfully. Preserve engineering values, "
                            "units, headings, and negations. Return page text only; do not interpret it."
                        ),
                    ],
                    config=types.GenerateContentConfig(temperature=0),
                )
            )
        except Exception as error:
            raise ProviderUnavailableError(
                f"Gemini scanned-page recovery failed: {error}"
            ) from error
        recovered = (getattr(response, "text", None) or "").strip()
        if not recovered:
            raise ProviderResponseError("Gemini scanned-page recovery returned no text")
        return recovered

    def generate_embedding(
        self, texts: list[str], *, task_type: str
    ) -> list[list[float]]:
        if not texts:
            return []
        contents = [
            types.Content(parts=[types.Part(text=text)], role="user") for text in texts
        ]
        try:
            response = self._call_with_transient_retry(
                lambda: self.client.models.embed_content(
                    model=self.embedding_model,
                    contents=contents,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=self.embedding_dimension,
                    ),
                )
            )
        except Exception as error:
            raise ProviderUnavailableError(f"Gemini embedding failed: {error}") from error
        vectors = [list(item.values or []) for item in (response.embeddings or [])]
        if len(vectors) != len(texts):
            raise ProviderResponseError("Gemini embedding count did not match the input count")
        if any(len(vector) != self.embedding_dimension for vector in vectors):
            raise ProviderResponseError(
                f"Gemini embedding dimension was not {self.embedding_dimension}"
            )
        return vectors

    def generate_answer(
        self,
        *,
        question: str,
        live_context: dict[str, object],
        evidence_bundle: list[dict[str, object]],
    ) -> GroundedAnswer:
        if not evidence_bundle:
            return GroundedAnswer(
                answer_markdown="The supplied evidence is insufficient to answer this question.",
                source_ids=[],
                insufficient_evidence=True,
            )
        allowed_ids = {
            str(item["source_id"]) for item in evidence_bundle if item.get("source_id")
        }
        prompt = json.dumps(
            {
                "question": question,
                "live_well_context": live_context,
                "evidence_bundle": evidence_bundle,
                "allowed_source_ids": sorted(allowed_ids),
            },
            ensure_ascii=False,
        )
        try:
            response = self._call_with_transient_retry(
                lambda: self.client.models.generate_content(
                    model=self.copilot_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=ANSWER_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=_gemini_wire_schema(GroundedAnswer),
                        temperature=0,
                    ),
                )
            )
        except Exception as error:
            raise ProviderUnavailableError(
                f"Gemini answer generation failed: {error}"
            ) from error
        answer = self._parse_structured(response, GroundedAnswer)
        assert isinstance(answer, GroundedAnswer)
        unknown = set(answer.source_ids) - allowed_ids
        if unknown:
            raise ProviderResponseError(
                f"Gemini answer invented citation IDs: {sorted(unknown)}"
            )
        if not answer.insufficient_evidence:
            if not answer.source_ids:
                raise ProviderResponseError("Gemini answer omitted required citations")
            missing_inline = [
                source_id
                for source_id in answer.source_ids
                if source_id not in answer.answer_markdown
            ]
            if missing_inline:
                raise ProviderResponseError(
                    f"Gemini answer omitted inline citations: {missing_inline}"
                )
        return answer
