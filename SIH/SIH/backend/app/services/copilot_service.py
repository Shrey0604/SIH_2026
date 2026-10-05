from __future__ import annotations

from typing import Any

from app.ai import AIProvider, ProviderResponseError, ProviderUnavailableError
from app.services.retrieval_service import RetrievalService


INSUFFICIENT_ANSWER = (
    "I couldn't find enough page-backed NWIS evidence to answer that. "
    "Try asking about a known formation, well, recorded hazard, or historical response."
)


class CopilotService:
    def __init__(self, retrieval: RetrievalService, provider: AIProvider | None):
        self.retrieval = retrieval
        self.provider = provider

    @staticmethod
    def _source_payload(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_id": item["source_id"],
            "event_id": item["event_id"],
            "well_name": item["well_name"],
            "formation": item["formation"],
            "hazard_type": item["hazard_type"],
            "document_id": item["document_id"],
            "document_title": item["document_title"],
            "filename": item["filename"],
            "page_number": item["page_number"],
            "evidence_text": item["evidence_text"],
            "source_kind": item["source_kind"],
        }

    @staticmethod
    def _deterministic_summary(evidence: list[dict[str, Any]]) -> str:
        lines = [
            "Generated synthesis unavailable — showing retrieved evidence.",
            "",
        ]
        for item in evidence[:3]:
            end_md = item["end_md_m"] if item["end_md_m"] is not None else item["start_md_m"]
            lines.append(
                f"- {item['well_name']} recorded {item['hazard_type'].replace('_', ' ').lower()} "
                f"in {item['formation']} at {item['start_md_m']:.0f}–{end_md:.0f} m MD "
                f"[{item['source_id']}]."
            )
            if item["historical_response"]:
                lines.append(
                    f"  Historical response observed: {item['historical_response']} "
                    f"[{item['source_id']}]."
                )
        return "\n".join(lines)

    def query(
        self,
        *,
        question: str,
        live_context: dict[str, object],
        selected_well_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        retrieved = self.retrieval.retrieve(
            question=question,
            formation=str(live_context.get("formation") or "") or None,
            selected_well_ids=selected_well_ids,
            top_k=6,
        )
        evidence = retrieved["evidence"]
        if not evidence:
            return {
                "answer_markdown": INSUFFICIENT_ANSWER,
                "sources": [],
                "insufficient_evidence": True,
                "generation_mode": "insufficient_evidence",
                "retrieval_mode": retrieved["retrieval_mode"],
                "retrieved_count": 0,
            }

        fallback_reason: str | None = None
        if self.provider is not None:
            try:
                answer = self.provider.generate_answer(
                    question=question,
                    live_context=live_context,
                    evidence_bundle=evidence,
                )
                allowed = {item["source_id"]: item for item in evidence}
                cited = [allowed[source_id] for source_id in answer.source_ids]
                minimum_citations = min(2, len(evidence))
                if not answer.insufficient_evidence and len(cited) < minimum_citations:
                    raise ProviderResponseError(
                        f"Grounded answer returned fewer than {minimum_citations} citations"
                    )
                return {
                    "answer_markdown": answer.answer_markdown,
                    "sources": [self._source_payload(item) for item in cited],
                    "insufficient_evidence": answer.insufficient_evidence,
                    "generation_mode": "gemini",
                    "retrieval_mode": retrieved["retrieval_mode"],
                    "retrieved_count": len(evidence),
                }
            except (ProviderUnavailableError, ProviderResponseError, KeyError) as error:
                fallback_reason = str(error)
        else:
            fallback_reason = "Gemini answer generation is unavailable"

        fallback_evidence = evidence[:3]
        return {
            "answer_markdown": self._deterministic_summary(fallback_evidence),
            "sources": [self._source_payload(item) for item in fallback_evidence],
            "insufficient_evidence": False,
            "generation_mode": "deterministic_evidence_summary",
            "retrieval_mode": retrieved["retrieval_mode"],
            "retrieved_count": len(evidence),
            "provider_error": fallback_reason,
        }
