from __future__ import annotations

from memory.vector_store import InMemoryVectorStore


class MemoryRetriever:
    def __init__(self, vector_store: InMemoryVectorStore) -> None:
        self.vector_store = vector_store

    def remember(self, record_id: str, text: str, metadata: dict | None = None) -> None:
        self.vector_store.upsert(record_id=record_id, text=text, metadata=metadata or {})

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        return [
            {
                "id": record.record_id,
                "text": record.text,
                "metadata": record.metadata,
            }
            for record in self.vector_store.search(query=query, top_k=top_k)
        ]
