from __future__ import annotations

from backend.services.embedding_service import EmbeddingService
from memory.document_store import ChromaDocumentStore
from memory.sparse_index import SparseKeywordIndex
from rag.schemas import RetrievalHit


class HybridRetriever:
    def __init__(
        self,
        document_store: ChromaDocumentStore,
        sparse_index: SparseKeywordIndex,
        embedding_service: EmbeddingService,
        vector_weight: float = 0.6,
        sparse_weight: float = 0.4,
    ) -> None:
        self.document_store = document_store
        self.sparse_index = sparse_index
        self.embedding_service = embedding_service
        self.vector_weight = vector_weight
        self.sparse_weight = sparse_weight

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalHit]:
        vector_hits = self.document_store.similarity_search(
            query_embedding=self.embedding_service.embed_query(query),
            top_k=top_k * 2,
        )
        sparse_hits = self.sparse_index.search(query=query, top_k=top_k * 2)

        merged: dict[str, RetrievalHit] = {}
        vector_scores = self._normalize_scores(vector_hits)
        sparse_scores = self._normalize_scores(sparse_hits)

        for hit in vector_hits:
            merged[hit.chunk_id] = RetrievalHit(
                chunk_id=hit.chunk_id,
                text=hit.text,
                score=vector_scores.get(hit.chunk_id, 0.0) * self.vector_weight,
                metadata=hit.metadata,
            )

        for hit in sparse_hits:
            if hit.chunk_id not in merged:
                merged[hit.chunk_id] = RetrievalHit(
                    chunk_id=hit.chunk_id,
                    text=hit.text,
                    score=0.0,
                    metadata=hit.metadata,
                )
            merged[hit.chunk_id].score += sparse_scores.get(hit.chunk_id, 0.0) * self.sparse_weight

        ranked = sorted(merged.values(), key=lambda item: item.score, reverse=True)
        return ranked[:top_k]

    @staticmethod
    def _normalize_scores(hits: list[RetrievalHit]) -> dict[str, float]:
        if not hits:
            return {}
        max_score = max(hit.score for hit in hits) or 1.0
        return {hit.chunk_id: hit.score / max_score for hit in hits}
