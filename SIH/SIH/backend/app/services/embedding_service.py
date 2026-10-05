from __future__ import annotations

from app.ai import AIProvider, ProviderUnavailableError
from app.config import Settings
from app.repositories.base import Repository


class EmbeddingService:
    """Centralizes retrieval-task formatting and embedding compatibility metadata."""

    def __init__(self, provider: AIProvider | None, settings: Settings):
        self.provider = provider
        self.provider_name = "gemini"
        self.model = settings.gemini_embedding_model
        self.dimension = settings.gemini_embedding_dim

    @staticmethod
    def format_document(document_title: str, chunk_text: str) -> str:
        return f"title: {document_title} | text: {chunk_text}"

    @staticmethod
    def format_query(query: str) -> str:
        return f"task: question answering | query: {query}"

    def embed_documents(
        self, document_title: str, chunk_texts: list[str]
    ) -> list[list[float]]:
        if self.provider is None:
            raise ProviderUnavailableError("GEMINI_API_KEY is unavailable for embeddings")
        formatted = [
            self.format_document(document_title, chunk_text) for chunk_text in chunk_texts
        ]
        return self.provider.generate_embedding(
            formatted, task_type="RETRIEVAL_DOCUMENT"
        )

    def embed_query(self, query: str) -> list[float]:
        if self.provider is None:
            raise ProviderUnavailableError("GEMINI_API_KEY is unavailable for embeddings")
        vectors = self.provider.generate_embedding(
            [self.format_query(query)], task_type="RETRIEVAL_QUERY"
        )
        return vectors[0]

    def invalidate_incompatible(self, repository: Repository) -> int:
        return repository.invalidate_incompatible_embeddings(
            provider=self.provider_name,
            model=self.model,
            dimension=self.dimension,
        )

    def rebuild_missing(self, repository: Repository) -> int:
        rebuilt = 0
        for document in repository.list_documents():
            chunks = [
                chunk
                for chunk in repository.list_document_chunks(document["id"])
                if chunk["embedding"] is None
            ]
            if not chunks:
                continue
            vectors = self.embed_documents(
                str(document["title"]), [str(chunk["text"]) for chunk in chunks]
            )
            repository.update_chunk_embeddings(
                [
                    {"id": chunk["id"], "embedding": vector}
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ],
                provider=self.provider_name,
                model=self.model,
                dimension=self.dimension,
            )
            rebuilt += len(chunks)
        return rebuilt

    def search(self, repository: Repository, query: str, *, top_k: int = 6):
        vector = self.embed_query(query)
        return repository.search_chunks(
            vector,
            provider=self.provider_name,
            model=self.model,
            dimension=self.dimension,
            top_k=top_k,
        )

    @property
    def metadata(self) -> dict[str, str | int]:
        return {
            "embedding_provider": self.provider_name,
            "embedding_model": self.model,
            "embedding_dimension": self.dimension,
        }
