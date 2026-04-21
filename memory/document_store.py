from __future__ import annotations

from pathlib import Path

from rag.schemas import DocumentChunk, RetrievalHit

import chromadb
class ChromaDocumentStore:
    def __init__(self, persist_path: str, collection_name: str = "uploaded_documents") -> None:
        self.persist_path = Path(persist_path)
        self.collection_name = collection_name
        self.persist_path = Path("/tmp/chroma_db")  # force safe path
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._collection = None
        self._available = None

  
    @property
    def is_available(self) -> bool:
        if self._available is None:
            try:
                self._available = self._ensure_collection() is not None
            except Exception:
                self._available = False
        return bool(self._available)
    @property
    def is_available(self) -> bool:
        if self._available is None:
            try:
                self._available = self._ensure_collection() is not None
            except Exception:
                self._available = False
        return bool(self._available)

    def upsert_chunks(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        collection = self._ensure_collection()
        if collection is None:
            raise RuntimeError("ChromaDB is not installed. Add `chromadb` to your environment.")

        collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[self._sanitize_metadata(chunk.metadata | {"document_id": chunk.document_id}) for chunk in chunks],
            embeddings=embeddings,
        )

    def similarity_search(self, query_embedding: list[float], top_k: int = 5) -> list[RetrievalHit]:
        collection = self._ensure_collection()
        if collection is None:
            return []

        result = collection.query(query_embeddings=[query_embedding], n_results=top_k)
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        hits: list[RetrievalHit] = []
        for chunk_id, text, metadata, distance in zip(ids, docs, metadatas, distances):
            hits.append(
                RetrievalHit(
                    chunk_id=chunk_id,
                    text=text,
                    score=1.0 / (1.0 + float(distance)),
                    metadata=metadata or {},
                )
            )
        return hits

    def list_documents(self) -> list[dict]:
        collection = self._ensure_collection()
        if collection is None:
            return []

        payload = collection.get(include=["metadatas"])
        seen: dict[str, dict] = {}
        for metadata in payload.get("metadatas", []):
            if not metadata:
                continue
            document_id = str(metadata.get("document_id", ""))
            if document_id and document_id not in seen:
                seen[document_id] = {
                    "document_id": document_id,
                    "file_name": metadata.get("file_name", ""),
                }
        return sorted(seen.values(), key=lambda item: item["file_name"])

    def has_documents(self) -> bool:
        return bool(self.list_documents())

    def _ensure_collection(self):
        if self._collection is not None:
            return self._collection

        try:
            import chromadb
        except Exception:
            self._available = False
            return None

        ##self._client = chromadb.PersistentClient(path=str(self.persist_path))
        self._client = chromadb.Client()  # in-memory (no SQLite issues)
        self._collection = self._client.get_or_create_collection(name=self.collection_name)
        self._available = True
        return self._collection

    @staticmethod
    def _sanitize_metadata(metadata: dict) -> dict:
        sanitized = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                sanitized[key] = value
            else:
                sanitized[key] = str(value)
        return sanitized
