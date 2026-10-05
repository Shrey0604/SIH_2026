from __future__ import annotations

import re
from typing import Any

from app.ai import ProviderResponseError, ProviderUnavailableError
from app.repositories.base import Repository
from app.services.embedding_service import EmbeddingService


TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "did",
    "do",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "our",
    "the",
    "this",
    "to",
    "us",
    "was",
    "were",
}
DOMAIN_INTENT_TERMS = {
    "ahead",
    "alert",
    "analog",
    "circulation",
    "event",
    "formation",
    "happened",
    "hazard",
    "historical",
    "history",
    "incident",
    "influx",
    "kick",
    "loss",
    "losses",
    "mitigation",
    "mud",
    "nearby",
    "offset",
    "pipe",
    "recorded",
    "response",
    "returns",
    "stuck",
    "support",
    "wells",
}
LIVE_CONTEXT_TERMS = {
    "ahead",
    "alert",
    "bit",
    "current",
    "here",
    "nearby",
    "offset",
    "support",
    "supporting",
    "window",
}


def _tokens(value: str) -> set[str]:
    return {token for token in TOKEN_RE.findall(value.casefold()) if token not in STOP_WORDS}


def _hazard_from_question(question: str) -> str | None:
    tokens = _tokens(question)
    if tokens & {"mud", "loss", "losses", "circulation", "returns"}:
        return "MUD_LOSS"
    if tokens & {"kick", "influx", "gas", "gain"}:
        return "KICK"
    if "stuck" in tokens or ({"pipe", "torque"} & tokens):
        return "STUCK_PIPE"
    return None


def _normalized_phrase(value: str) -> str:
    return " ".join(TOKEN_RE.findall(value.casefold()))


def _mentions(question: str, value: str) -> bool:
    normalized_question = f" {_normalized_phrase(question)} "
    normalized_value = _normalized_phrase(value)
    return bool(normalized_value) and f" {normalized_value} " in normalized_question


class RetrievalService:
    """Evidence-first retrieval shared by knowledge search and copilot."""

    def __init__(self, repository: Repository, embeddings: EmbeddingService | None):
        self.repository = repository
        self.embeddings = embeddings

    def search_events(
        self,
        *,
        query: str | None = None,
        well_id: str | None = None,
        formation: str | None = None,
        hazard_type: str | None = None,
    ) -> list[dict[str, Any]]:
        query_tokens = _tokens(query or "")
        well_names = {well["id"]: well["name"] for well in self.repository.list_wells()}
        ranked: list[dict[str, Any]] = []
        for event in self.repository.list_events():
            if well_id and event["well_id"] != well_id:
                continue
            if formation and (event["formation_name"] or "").casefold() != formation.casefold():
                continue
            if hazard_type and event["hazard_type"] != hazard_type:
                continue
            detail = self.repository.get_event(str(event["id"]))
            if detail is None or not detail["evidence"]:
                continue
            evidence_text = " ".join(
                str(reference["evidence_text"]) for reference in detail["evidence"]
            )
            searchable = " ".join(
                str(value or "")
                for value in (
                    event["hazard_type"].replace("_", " "),
                    event["formation_name"],
                    well_names.get(str(event["well_id"]), ""),
                    event["description"],
                    event["historical_response"],
                    evidence_text,
                )
            )
            searchable_tokens = _tokens(searchable)
            if query_tokens and not query_tokens.intersection(searchable_tokens):
                continue
            overlap = len(query_tokens.intersection(searchable_tokens))
            score = overlap / max(1, len(query_tokens))
            ranked.append(
                detail
                | {
                    "search_score": round(score, 6),
                    "evidence_preview": detail["evidence"][0]["evidence_text"],
                }
            )
        return sorted(
            ranked,
            key=lambda item: (
                item["search_score"],
                item["extraction_confidence"],
                item["id"],
            ),
            reverse=True,
        )

    def retrieve(
        self,
        *,
        question: str,
        formation: str | None = None,
        selected_well_ids: list[str] | None = None,
        top_k: int = 6,
    ) -> dict[str, Any]:
        question_tokens = _tokens(question)
        formation_names = sorted(
            {
                str(interval["formation_name"])
                for interval in self.repository.list_formation_intervals()
                if interval.get("formation_name")
            }
        )
        wells = self.repository.list_wells()
        mentioned_formation = next(
            (name for name in formation_names if _mentions(question, name)), None
        )
        mentioned_well = next(
            (well for well in wells if _mentions(question, str(well["name"]))), None
        )
        has_domain_anchor = bool(
            question_tokens.intersection(DOMAIN_INTENT_TERMS)
            or mentioned_formation
            or mentioned_well
        )
        if not has_domain_anchor:
            return {
                "evidence": [],
                "retrieval_mode": "insufficient",
                "embedding_error": None,
                "matched_formation": None,
                "matched_well_id": None,
            }

        inferred_hazard = _hazard_from_question(question)
        use_live_context = bool(question_tokens.intersection(LIVE_CONTEXT_TERMS))
        target_formation = mentioned_formation or (formation if use_live_context else None)
        target_well_id = str(mentioned_well["id"]) if mentioned_well else None
        selected = set(selected_well_ids or []) if use_live_context and not target_well_id else set()
        vector_matches: list[dict[str, Any]] = []
        embedding_error: str | None = None
        if self.embeddings is not None:
            try:
                vector_matches = self.embeddings.search(
                    self.repository, question, top_k=max(top_k * 2, 8)
                )
            except (ProviderUnavailableError, ProviderResponseError, ValueError) as error:
                embedding_error = str(error)

        vector_scores = {
            (str(item["document_id"]), int(item["page_number"])): max(
                0.0, float(item["similarity"])
            )
            for item in vector_matches
        }
        candidates = self.search_events(
            well_id=target_well_id,
            formation=target_formation,
            hazard_type=inferred_hazard,
        )
        ranked: list[dict[str, Any]] = []
        for event in candidates:
            if selected and event["well_id"] not in selected:
                continue
            event_text = " ".join(
                str(value or "")
                for value in (
                    event["hazard_type"].replace("_", " "),
                    event["formation_name"],
                    event["well_name"],
                    event["description"],
                    event["historical_response"],
                    event["evidence_preview"],
                )
            )
            event_tokens = _tokens(event_text)
            overlap = len(question_tokens.intersection(event_tokens)) / max(
                1, len(question_tokens)
            )
            for reference in event["evidence"]:
                vector_score = vector_scores.get(
                    (str(reference["document_id"]), int(reference["page_number"])), 0.0
                )
                metadata_score = 0.0
                if target_formation and (
                    event["formation_name"] or ""
                ).casefold() == target_formation.casefold():
                    metadata_score += 0.18
                if target_well_id and event["well_id"] == target_well_id:
                    metadata_score += 0.18
                if selected and event["well_id"] in selected:
                    metadata_score += 0.18
                if inferred_hazard and event["hazard_type"] == inferred_hazard:
                    metadata_score += 0.22
                rank_score = 0.42 * overlap + 0.30 * vector_score + metadata_score
                ranked.append(
                    {
                        "source_id": reference["id"],
                        "event_id": event["id"],
                        "well_id": event["well_id"],
                        "well_name": event["well_name"],
                        "formation": event["formation_name"],
                        "hazard_type": event["hazard_type"],
                        "start_md_m": event["start_md_m"],
                        "end_md_m": event["end_md_m"],
                        "severity": event["severity"],
                        "description": event["description"],
                        "historical_response": event["historical_response"],
                        "document_id": reference["document_id"],
                        "document_title": reference["document_title"],
                        "filename": reference["filename"],
                        "page_number": reference["page_number"],
                        "evidence_text": reference["evidence_text"],
                        "source_kind": reference["source_kind"],
                        "rank_score": round(rank_score, 6),
                        "vector_similarity": round(vector_score, 6),
                    }
                )
        ranked.sort(
            key=lambda item: (item["rank_score"], item["source_id"]), reverse=True
        )
        return {
            "evidence": ranked[:top_k],
            "retrieval_mode": "hybrid" if vector_matches else "metadata_lexical",
            "embedding_error": embedding_error,
            "matched_formation": mentioned_formation,
            "matched_well_id": target_well_id,
        }
